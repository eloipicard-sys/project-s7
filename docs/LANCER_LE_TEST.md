# 🚀 Comment tester Docker avec ce projet

## Prérequis
Docker Desktop doit être démarré (icône verte dans la barre des tâches).

## Étapes

### 1. Ouvre PowerShell dans ce dossier

Fais un clic droit dans le dossier `test_docker/` → "Ouvrir dans Terminal"

### 2. Lance l'application

```powershell
docker compose up -d --build
```

Tu verras Docker :
- Télécharger l'image Python
- Installer Flask
- Démarrer l'application

### 3. Vérifie que ça tourne

```powershell
docker compose ps
```
→ Le statut doit être `running (healthy)`

### 4. Ouvre l'interface web

👉 http://localhost:5000

Tu dois voir la page de supervision thermique avec des données simulées.

### 5. Teste l'API JSON

👉 http://localhost:5000/api/data

Tu dois recevoir un JSON avec température, débit, etc.

### 6. Voir les logs en temps réel

```powershell
docker compose logs -f
```

### 7. Arrêter le test

```powershell
docker compose down
```

---

## ✅ Si tout fonctionne → Docker est prêt pour le projet S7-1500 !

Prochaine étape : décommenter `python-snap7` dans `requirements.txt`
et remplacer la simulation dans `main.py` par les vraies lectures Snap7.
