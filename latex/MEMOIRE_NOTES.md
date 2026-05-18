# Procédé thermique S7-1500 — Notes de projet & Plan du mémoire

---

## 1. Session du 18 mai 2026 — Travail accompli

### 1.1 Infrastructure & réseau

| Équipement | IP | Rôle |
|------------|-----|------|
| S7-1500 CPU | 192.168.1.10 | Automate (mis à jour depuis .100) |
| SIMATIC Panel 7" | 192.168.1.200 | WinCC Unified + Edge Runtime |
| PC développement | 192.168.1.149 | Docker, TIA Portal |

Pare-feu Windows : règle ajoutée pour port 5000 → accès panel vers app.

### 1.2 TIA Portal

- DB1 créé avec **Optimized block access désactivé** (requis par Snap7)
- Table des variables nettoyée : **21 tags process conservés**, 25 supprimés
- Convention de nommage anglaise adoptée : `Tin1_HE1`, `Tout2_HE1`, `Valve_F1`, etc.
- Adresses retenues :

| Tag | Type | Adresse |
|-----|------|---------|
| T_hin | Real | %MD16 |
| T_hout | Real | %MD12 |
| T_we_rock_furnace | Int | %IW300 |
| T_wy_Oven_scale | Int | %IW304 |
| Tin1_HE1 | Real | %MD48 |
| Tout1_HE1 | Real | %MD44 |
| Tin2_HE1 | Real | %MD40 |
| Tout2_HE1 | Real | %MD52 |
| Tin1_heat_exchanger1_scale | Int | %IW112 |
| Tout1_HE1_raw | Int | %IW120 |
| Tin2_HE1_raw | Int | %IW116 |
| Tout2_HE1_raw | Int | %IW108 |
| F1 | Real | %MD28 |
| F1_SP | Real | %MD24 |
| F1_skal | Int | %IW316 |
| Valve_F1 | Word | %QW8 |
| F2 | Real | %MD32 |
| F2_SP | Real | %MD36 |
| F2_skal | Int | %IW204 |
| Valve_F2 | Int | %QW4 |
| power | Bool | %Q0.3 |

### 1.3 Application Flask — nouvelles fonctionnalités

- Page `/cascade` avec deux onglets :
  - **Identification** : test échelon F1_SP → calcul automatique K / τ / θ → gains IMC
  - **Contrôle cascade** : PI+P interne (Tin1 → F1) + P externe (Tout2 → Tin1_SP), 3 modes (Manuel / Auto interne / Auto cascade)
- Tous les noms de tags synchronisés dans `openpipe_connector.py`, `main.py`, `schema.html`, `process.html`
- Règle pare-feu Windows ajoutée pour accès depuis le panel

---

## 2. Session du 19 mai 2026 — Plan d'expérience

### 2.1 Objectifs

1. Acquérir des données réelles sur l'installation en régime établi
2. Identifier le modèle dynamique boucle interne (Tin1 / F1_SP)
3. Confirmer la structure de contrôle cascade avec Michal
4. Tester la boucle interne en mode Auto et vérifier la stabilité

### 2.2 Protocole — Test échelon

**Conditions initiales :**
- Four allumé, régime permanent établi (≥ 30 min de chauffe)
- F1_SP au point de fonctionnement nominal
- Cascade en mode **Manuel** obligatoire avant de démarrer

**Paramètres recommandés :**

| Paramètre | Valeur |
|-----------|--------|
| F1_SP base | Valeur courante lue sur PLC (auto-remplie) |
| Amplitude | +0.5 m³/h (≈ 15% de la plage) |
| Durée | 180 s minimum |
| URL | `http://192.168.1.149:5000/cascade` |

**Résultats attendus :**

| Paramètre | Signification | Ordre de grandeur typique |
|-----------|--------------|--------------------------|
| K | Gain statique ΔTin1 / ΔF1_SP | 5–30 °C/(m³/h) |
| τ | Constante de temps (63,2%) | 30–120 s |
| θ | Retard pur | 3–15 s |

### 2.3 Questions à clarifier avec Michal

- [ ] Structure exacte boucle externe : P ou PI ? (impact sur l'offset statique)
- [ ] Limites opérationnelles réelles de F1_SP (min / max en m³/h)
- [ ] Protocole Open Pipe : nom exact du socket et format JSON WinCC Unified
- [ ] Cohérence adresses %IW : valider en config matérielle TIA Portal
- [ ] Licences Industrial Edge : obtenir identifiants pour import de l'app `.app`

---

## 3. Architecture du projet

### 3.1 Infrastructure physique

```
Réseau local 192.168.1.x (switch industriel)
    ├── S7-1500 CPU          192.168.1.10
    │       └── DB1 (Snap7), %MD (Open Pipe), %IW/%Q (I/O physique)
    ├── SIMATIC Panel 7"     192.168.1.200
    │       ├── WinCC Unified Runtime (tags + Open Pipe socket)
    │       └── Industrial Edge Runtime (port 30500)
    └── PC développement     192.168.1.149
            ├── Docker Desktop (app Flask port 5000)
            └── TIA Portal V18
```

### 3.2 Stack logicielle

```
Docker container — s7-thermal-app
├── main.py                    Flask app, routes HTTP, Socket.IO, threads
├── openpipe_connector.py      Lecture/écriture tags WinCC via socket Unix
├── plc_connector.py           Lecture/écriture DB1 via Snap7 (TCP)
├── cascade_controller.py      PI+P interne + P externe, bumpless transfer
├── identification.py          Test échelon, méthode 63,2%, réglage IMC
├── thermal_model.py           Simulation 1er ordre (fallback sans PLC)
├── logger.py                  Log CSV append-only
└── templates/
    ├── schema.html            Synoptique P&ID (panel 7")
    ├── cascade.html           Identification + contrôle cascade (PC)
    ├── process.html           Table 21 tags (debug)
    ├── index.html             Monitor Chart.js (debug)
    └── test.html              Lecture/écriture DB1 (debug)
```

### 3.3 Flux de données

```
Capteurs physiques (%IW)
  → FC scaling dans OB1 TIA Portal
  → Mémoire PLC (%MD / %Q)
  → Open Pipe socket (Unix)
  → openpipe_connector.py  (poll every 3s)
  → Socket.IO broadcast 'process_tags'
  → Navigateur (schema.html, cascade.html, process.html)

cascade_controller.py (thread)
  → Calcule F1_SP (PI+P + P externe)
  → openpipe_connector.py write %MD24
  → Automate → Valve_F1 (%QW8)
```

### 3.4 Threads applicatifs

| Thread | Rôle | Intervalle |
|--------|------|-----------|
| `sim-loop` | Avance le modèle thermique (fallback) | 3 s |
| `plc-poll` | Lit DB1 via Snap7 si PLC connecté | 3 s |
| `openpipe-poll` | Lit les 21 tags + exécute cascade/identification | 3 s |

---

## 4. Stratégie de contrôle

### 4.1 Objectif

Maintenir **Tout2_HE1** (sortie côté froid) à consigne, en manipulant **F1_SP** (débit flux chaud).

### 4.2 Structure cascade

```
Tout2_SP ──→ [ P externe ] ──→ Tin1_SP_cmd ──→ [ PI+P interne ] ──→ F1_SP
                  ↑                                     ↑
               Tout2_HE1                            Tin1_HE1
```

**Boucle interne — PI avec P sur la mesure (velocity form) :**

```
Δu[k] = −Kp × (Tin1[k] − Tin1[k−1]) + (Kp/Ti) × e[k] × dt
u[k]  = u[k−1] + Δu[k]          (saturé à [0, F1_max])
```
- Pas de choc proportionnel sur changement de consigne
- Transfert sans choc : `init_output(F1_SP_courant, Tin1_courant)` avant passage Auto

**Boucle externe — P (à confirmer PI) :**
```
Tin1_SP_cmd = Tin1_SP_base + Kp_ext × (Tout2_SP − Tout2)
```

### 4.3 Identification — Méthode des 63,2%

| Paramètre | Formule |
|-----------|---------|
| K | `ΔTin1_final / ΔF1_SP` |
| τ | Temps pour atteindre `Tin1_base + 0,632 × ΔTin1` depuis le saut |
| θ | Délai avant que `|ΔTin1| > 2%` de l'amplitude totale |

**Réglage IMC :**
```
Kp = τ / (K × (λ + θ))     Ti = τ
λ = τ     (normal)
λ = 0.5τ  (agressif)
λ = 2τ    (conservatif)
```

---

## 5. Ébauche du plan de mémoire

> **Titre provisoire**
> *Supervision et contrôle en cascade d'un procédé thermique sur automate Siemens S7-1500 avec interface web embarquée*

---

### Introduction
- Contexte : supervision des procédés thermiques en industrie
- Problématique : comment intégrer une supervision web moderne avec un automate industriel standard ?
- Objectifs : identification, régulation cascade, interface embarquée sur panel
- Plan du mémoire

---

### Chapitre 1 — Le procédé thermique étudié
- Description de l'installation : four électrique, échangeur à plaques HE-001, circuits F1 (chaud) / F2 (froid)
- Variables du procédé : températures (Tin1, Tout2…), débits (F1, F2), vannes (Valve_F1/F2)
- Instrumentation : capteurs analogiques, modules I/O S7-1500
- Schéma P&ID de l'installation

---

### Chapitre 2 — L'automate S7-1500 et l'environnement Siemens
- Architecture CPU S7-1500 : cycle d'exécution, organisation mémoire, blocs (OB/FC/DB)
- Programmation TIA Portal V18 : table des tags, FC de scaling, DB1 (adressage absolu)
- WinCC Unified : runtime sur SIMATIC Panel 7", table des variables, supervision locale
- Open Pipe : communication temps réel entre WinCC Unified et application externe
- Industrial Edge : déploiement d'application Docker sur panel via App Publisher

---

### Chapitre 3 — Architecture logicielle de supervision
- Choix technologiques : Python/Flask, Socket.IO, Chart.js, Docker
- Organisation du code : threads, flux de données, API REST
- Communication PLC ↔ App : Snap7 (DB1 direct) et Open Pipe (tags WinCC Unified)
- Déploiement : Docker sur PC de développement, port 5000 ; edge sur panel, port 30500
- Pages de supervision : Synoptique (panel), Cascade (PC), Process, Monitor

---

### Chapitre 4 — Identification expérimentale du procédé
- Modèle du 1er ordre avec retard (FOPTD) : justification théorique
- Méthode expérimentale : test échelon en boucle ouverte sur F1_SP
- Protocole : conditions initiales, amplitude, durée, acquisition via Socket.IO
- Résultats : courbes de réponse, extraction K / τ / θ par la méthode des 63,2%
- Réglage des gains PI par la méthode IMC : comparaison agressif / normal / conservatif

---

### Chapitre 5 — Contrôle en cascade
- Justification du contrôle cascade vs PID simple sur Tout2
- Boucle interne : PI avec P sur la mesure (velocity form), implémentation Python, anti-emballement
- Boucle externe : contrôleur proportionnel (P), discussion sur l'offset statique résiduel
- Transfert sans choc : initialisation `init_output()` lors du passage Manuel → Auto
- Validation expérimentale : réponses indicielle et de rejet de perturbation

---

### Chapitre 6 — Interface de supervision
- Synoptique P&ID temps réel (schema.html) : conception pour panel 7" tactile
- Page Cascade (cascade.html) : outil d'identification et de mise en route
- Expérience utilisateur : lisibilité à distance, interaction tactile, temps de réponse Socket.IO
- Données : log CSV, export, statistiques

---

### Conclusion
- Bilan : modèle identifié, régulation cascade opérationnelle, supervision embarquée sur panel
- Limites : résolution d'identification limitée à 3 s/échantillon, offset boucle externe avec P seul
- Perspectives : boucle externe PI, intégration Open Pipe complète, alarmes côté PLC, déploiement Edge final

---

### Annexes
- A — Table des 21 tags WinCC Unified (noms, types, adresses)
- B — Structure de DB1 (offset Snap7)
- C — Extraits de code commentés (cascade_controller.py, identification.py)
- D — Courbes d'identification expérimentales (K, τ, θ)
- E — Manuel d'utilisation de l'interface web
