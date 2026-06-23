"""
Cascade PI+P controller — thermal process, Politechnika Śląska.

Inner loop : Tin1 (measured) → PWM heater (%)   — PI with P on measurement
Outer loop : Tout2 (measured) → Tin1_SP (°C)    — Proportional

Gain scheduling: Kp and Ti are interpolated from the FOPTD identification
table (4 operating points at F1 = 1, 2, 3, 4 L/min).
"""
import threading
from typing import Optional


# ── Gain scheduling — power-law fit on K, τ, θ (23/06/2026 identification) ────
# Fits computed with scipy.optimize.curve_fit on 4 operating points (1–4 L/min).
# K(F)   = 1.6195 * F^(-1.0702)   [°C/%]
# tau(F) = 114.77 * F^(-0.8889)   [s]
# tht(F) = 26.66  * F^(-0.7469)   [s]
# IMC Normal: lambda = tau, Kp = tau / (K * (tau + tht)), Ti = tau

_AK,  _BK  = 1.6195, -1.0702
_AT,  _BT  = 114.77, -0.8889
_ATH, _BTH = 26.66,  -0.7469
_F_MIN, _F_MAX = 1.0, 4.0


def _interpolate_gains(F1: float) -> tuple[float, float]:
    """Return (Kp, Ti) from power-law gain scheduling given flow F1 (L/min)."""
    F = max(_F_MIN, min(_F_MAX, F1))
    K_f   = _AK  * F ** _BK
    tau_f = _AT  * F ** _BT
    tht_f = _ATH * F ** _BTH
    lam   = max(tau_f, tht_f)
    kp    = tau_f / (K_f * (lam + tht_f))
    ti    = tau_f
    return kp, ti


class PIplusP:
    """
    Discrete PI — velocity (incremental) form with proportional on measurement.
    Avoids proportional kick on setpoint step changes.
    Call init_output() before switching from manual to auto for bumpless transfer.
    """

    def __init__(self, Kp: float = 1.0, Ti: float = 60.0,
                 out_min: float = 0.0, out_max: float = 100.0, dt: float = 3.0):
        self.Kp = Kp
        self.Ti = Ti
        self.out_min = out_min
        self.out_max = out_max
        self.dt = dt
        self.last_output: float = (out_min + out_max) / 2.0
        self._last_meas: Optional[float] = None

    def update(self, setpoint: float, measurement: float) -> float:
        if self._last_meas is None:
            self._last_meas = measurement
        error = setpoint - measurement
        delta_u = (-self.Kp * (measurement - self._last_meas)
                   + (self.Kp / max(self.Ti, 0.01)) * error * self.dt)
        clamped = max(self.out_min, min(self.out_max, self.last_output + delta_u))
        self.last_output = clamped
        self._last_meas = measurement
        return clamped

    def init_output(self, current_output: float, current_meas: float):
        self.last_output = current_output
        self._last_meas = current_meas


class CascadeController:
    """
    Two-level cascade controller with gain scheduling.

    Modes:
        'manual'      — no automatic output
        'auto_inner'  — inner PI+P active (Tin1 → PWM), outer setpoint manual
        'auto_full'   — both loops active (Tout2_SP → Tin1_SP → PWM)
    """

    MODE_MANUAL     = 'manual'
    MODE_AUTO_INNER = 'auto_inner'
    MODE_AUTO_FULL  = 'auto_full'

    def __init__(self):
        self._lock = threading.Lock()
        self.mode: str = self.MODE_MANUAL

        # Inner PI+P: Tin1 → PWM (%)
        self.inner = PIplusP(Kp=1.0, Ti=60.0, out_min=0.0, out_max=100.0, dt=3.0)

        # Outer proportional: Tout2 → Tin1_SP (°C)
        self.outer_Kp: float = 2.0
        self.outer_out_min: float = 20.0
        self.outer_out_max: float = 200.0

        # Setpoints (operator input)
        self.Tout2_SP: float = 50.0
        self.Tin1_SP:  float = 60.0

        # Last computed values (for status display)
        self.Tin1_SP_cmd: float = 60.0
        self.PWM_out:     float = 0.0
        self.last_Tin1:   Optional[float] = None
        self.last_Tout2:  Optional[float] = None
        self.last_F1:     float = 2.0
        self.gain_scheduled: bool = True   # set False to fix gains manually

    def update(self, Tin1: float, Tout2: float, F1: float = 2.0) -> Optional[float]:
        """
        Run one control cycle. Returns PWM command (%) to write, or None if manual.
        F1 (L/min) is used for gain scheduling.
        """
        with self._lock:
            self.last_Tin1  = Tin1
            self.last_Tout2 = Tout2
            self.last_F1    = F1

            if self.gain_scheduled:
                kp, ti = _interpolate_gains(F1)
                self.inner.Kp = kp
                self.inner.Ti = ti

            if self.mode == self.MODE_MANUAL:
                return None

            if self.mode == self.MODE_AUTO_FULL:
                raw = self.Tin1_SP + self.outer_Kp * (self.Tout2_SP - Tout2)
                self.Tin1_SP_cmd = max(self.outer_out_min,
                                       min(self.outer_out_max, raw))
            else:
                self.Tin1_SP_cmd = self.Tin1_SP

            pwm = self.inner.update(self.Tin1_SP_cmd, Tin1)
            self.PWM_out = pwm
            return pwm

    def set_mode(self, mode: str,
                 current_PWM: float = 0.0, current_Tin1: float = 0.0):
        with self._lock:
            if mode not in (self.MODE_MANUAL, self.MODE_AUTO_INNER, self.MODE_AUTO_FULL):
                raise ValueError(f"Unknown mode: {mode}")
            if self.mode == self.MODE_MANUAL and mode != self.MODE_MANUAL:
                self.inner.init_output(current_PWM, current_Tin1)
            self.mode = mode

    def set_inner_params(self, Kp: float, Ti: float):
        with self._lock:
            self.inner.Kp = Kp
            self.inner.Ti = max(Ti, 0.1)
            self.gain_scheduled = False  # manual override disables scheduling

    def set_outer_params(self, Kp: float):
        with self._lock:
            self.outer_Kp = Kp

    def enable_gain_scheduling(self):
        with self._lock:
            self.gain_scheduled = True

    def set_Tout2_SP(self, value: float):
        with self._lock:
            self.Tout2_SP = value

    def set_Tin1_SP(self, value: float):
        with self._lock:
            self.Tin1_SP = value

    def get_status(self) -> dict:
        with self._lock:
            Tin1  = self.last_Tin1
            Tout2 = self.last_Tout2
            return {
                'mode':             self.mode,
                'Tout2_SP':         self.Tout2_SP,
                'Tin1_SP':          self.Tin1_SP,
                'Tin1_SP_cmd':      round(self.Tin1_SP_cmd, 2),
                'PWM_out':          round(self.PWM_out, 1),
                'F1':               round(self.last_F1, 2),
                'gain_scheduled':   self.gain_scheduled,
                'Tin1':             round(Tin1, 2)  if Tin1  is not None else None,
                'Tout2':            round(Tout2, 2) if Tout2 is not None else None,
                'err_Tin1':         round(self.Tin1_SP_cmd - Tin1, 2) if Tin1 is not None else None,
                'err_Tout2':        round(self.Tout2_SP - Tout2, 2)   if Tout2 is not None else None,
                'inner_Kp':         round(self.inner.Kp, 4),
                'inner_Ti':         round(self.inner.Ti, 1),
                'outer_Kp':         self.outer_Kp,
            }
