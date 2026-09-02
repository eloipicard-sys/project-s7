"""
Modèle de simulation du procédé thermique.

Remplace le bouchon de valeurs qui servait jusqu'ici : toutes les températures y
dérivaient d'une même onde triangulaire, si bien que Tout2 ne présentait aucun
retard sur Tin1 et lui était même supérieure, ce qui est thermodynamiquement
impossible dans un échangeur.

Le modèle reproduit la structure identifiée expérimentalement le 23/06/2026 :

    PWM ──[retard θ₁ + 1er ordre τ₁]──> Tin1 ──[retard θ₂ + 1er ordre τ₂]──> Tout2

Les paramètres de la boucle interne viennent des lois de puissance ajustées sur
les quatre essais (cf. cascade_controller.py). Ceux de la boucle externe ne sont
pas encore identifiés : les valeurs retenues sont des ordres de grandeur
plausibles, à remplacer après la campagne en boucle fermée.
"""
import time
import threading
from collections import deque


# ── Boucle interne : PWM → Tin1, lois ajustées sur l'identification ───────────
_AK,  _BK  = 1.6195, -1.0702      # K(F)   = a·F^b   [°C/%]
_AT,  _BT  = 114.77, -0.8889      # tau(F) = a·F^b   [s]
_ATH, _BTH = 26.66,  -0.7469      # theta(F) = a·F^b [s]
_F_MIN, _F_MAX = 1.0, 4.0

# ── Boucle externe : Tin1 → Tout2 (non identifiée, ordres de grandeur) ────────
_K2     = 0.55     # gain statique [°C/°C] : l'échangeur ne transmet qu'une part
_TAU2   = 180.0    # constante de temps [s] : masse thermique des plaques
_THETA2 = 25.0     # retard pur [s] : transport du fluide

_T_AMBIENT = 21.0  # température de repos, four éteint


class ProcessSimulator:
    """
    Simule la réponse thermique du banc à la commande PWM.

    Intégration à pas variable (Euler explicite) : le pas réel entre deux appels
    est mesuré, ce qui rend le modèle indépendant de la cadence d'appel.
    """

    def __init__(self, pwm: float = 30.0, f1: float = 2.0, f2: float = 1.8):
        self._lock = threading.Lock()
        self._pwm  = pwm
        self._f1   = f1
        self._f2   = f2

        # Files de retard : (instant, valeur)
        self._pwm_hist  = deque(maxlen=4000)
        self._tin1_hist = deque(maxlen=4000)

        # États, initialisés au régime permanent correspondant au PWM de départ
        K, _, _ = self._inner_params(f1)
        self._tin1 = _T_AMBIENT + K * pwm
        self._tout2 = _T_AMBIENT + _K2 * (self._tin1 - _T_AMBIENT)
        self._last_t = time.time()

    # ── Paramètres dépendant du débit ────────────────────────────────────────

    @staticmethod
    def _inner_params(f1: float):
        """(K, tau, theta) de la boucle interne au débit f1, bornés à la plage testée."""
        f = max(_F_MIN, min(_F_MAX, f1))
        return (_AK * f ** _BK, _AT * f ** _BT, _ATH * f ** _BTH)

    # ── Commandes ────────────────────────────────────────────────────────────

    def set_pwm(self, pwm: float) -> None:
        with self._lock:
            self._pwm = max(0.0, min(100.0, float(pwm)))

    def set_flows(self, f1: float = None, f2: float = None) -> None:
        with self._lock:
            if f1 is not None:
                self._f1 = max(0.1, float(f1))
            if f2 is not None:
                self._f2 = max(0.1, float(f2))

    # ── Avancement ───────────────────────────────────────────────────────────

    def _delayed(self, hist: deque, now: float, theta: float, fallback: float) -> float:
        """Valeur de l'historique telle qu'elle était il y a theta secondes."""
        target = now - theta
        best = fallback
        for t, v in hist:
            if t <= target:
                best = v
            else:
                break
        return best

    def step(self) -> dict:
        """Avance le modèle jusqu'à maintenant et renvoie l'état courant."""
        with self._lock:
            now = time.time()
            dt = now - self._last_t
            self._last_t = now
            # Un pas aberrant (veille de la machine, point d'arrêt) ne doit pas
            # faire diverger l'intégration.
            dt = max(0.0, min(dt, 10.0))

            self._pwm_hist.append((now, self._pwm))
            K, tau, theta = self._inner_params(self._f1)

            # Étage 1 : PWM retardé → Tin1
            pwm_eff = self._delayed(self._pwm_hist, now, theta, self._pwm)
            tin1_cible = _T_AMBIENT + K * pwm_eff
            self._tin1 += dt / tau * (tin1_cible - self._tin1)

            self._tin1_hist.append((now, self._tin1))

            # Étage 2 : Tin1 retardée → Tout2
            tin1_eff = self._delayed(self._tin1_hist, now, _THETA2, self._tin1)
            tout2_cible = _T_AMBIENT + _K2 * (tin1_eff - _T_AMBIENT)
            self._tout2 += dt / _TAU2 * (tout2_cible - self._tout2)

            return self._snapshot()

    def _snapshot(self) -> dict:
        """
        Températures dérivées, ordonnées de façon physiquement cohérente :
        le fluide chaud cède de l'énergie, le fluide froid en gagne.
        """
        tin1  = self._tin1
        tout1 = _T_AMBIENT + 0.72 * (tin1 - _T_AMBIENT)   # sortie chaude, refroidie
        tin2  = _T_AMBIENT + 2.0                          # entrée froide, quasi constante
        tout2 = self._tout2                               # sortie froide, réchauffée
        return {
            "Tin1":  round(tin1, 1),
            "Tout1": round(tout1, 1),
            "Tin2":  round(tin2, 1),
            "Tout2": round(tout2, 1),
            "T_hout": round(tin1 + 1.5, 1),               # sortie four, avant pertes de ligne
            "T_hin":  round(tout1 - 1.0, 1),              # retour au four
            "PWM":   round(self._pwm, 1),
            "F1":    round(self._f1, 2),
            "F2":    round(self._f2, 2),
        }
