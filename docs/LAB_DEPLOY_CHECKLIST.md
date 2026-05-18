# Déploiement panel — Checklist labo

**Fichier à déployer** : `C:\Users\eloip\project-s7\dist\S7 - 1500 Thermal Monitor_1.0.0.app` (52 MB)

---

## 1. Connexion au panel

- Ouvre un navigateur (Chrome/Edge) → `https://<IP-du-panel>`
- ⚠️ HTTPS obligatoire, pas HTTP
- Avertissement certificat auto-signé → *Avancé* → *Continuer vers le site*
- Login : `admin` + mot de passe défini lors de la mise en service

## 2. Vérifier que le runtime Edge tourne

- Une fois connecté, tu dois voir un dashboard avec **CPU / RAM / Apps**
- Si tu vois un message "*Edge Runtime not activated*" → menu **System Settings** → **Edge Runtime** → *Activate*
  *(peut prendre 2 min, l'IED redémarre)*

## 3. Installer le .app

- Menu **Apps** (ou **Applications**, **Local apps** selon la version firmware)
- Bouton **+ Install offline app** / *Import application* / *Upload .app*
- Sélectionne `S7 - 1500 Thermal Monitor_1.0.0.app` depuis ta clé USB ou via le partage réseau
- Attends 3–8 min : signature → décompression → import image Docker → création conteneur

## 4. Avant de lancer — vérifier la config

L'app embarque `PLC_IP=192.168.1.100`. **Si ton PLC labo a une autre IP**, il faut la corriger AVANT le démarrage :

- Sur la fiche de l'app installée → **Configuration** ou **Settings** → **Environment Variables**
- Modifie `PLC_IP` pour matcher l'IP réelle du S7-1500 sur le réseau labo
- Save

Variables à vérifier :

| Variable | Valeur par défaut | À changer si... |
|---|---|---|
| `PLC_IP` | `192.168.1.100` | IP réelle du S7-1500 différente |
| `PLC_RACK` | `0` | toujours 0 sur S7-1500 |
| `PLC_SLOT` | `1` | toujours 1 sur S7-1500 |
| `PLC_DB` | `1` | si DB1 réservé pour autre chose |
| `FLASK_DEBUG` | `0` | laisse 0 en prod |
| `PORT` | `5000` | ne touche pas |

## 5. Démarrer l'app

- Bouton **Start** ou icône ▶️ sur la fiche de l'app
- Statut doit passer à **Running** (vert) en 30–60 sec
- Si **Crashed** ou **OOM Killed** dans les logs → mémoire insuffisante, à rebuilder en augmentant `mem_limit` à 768 MB ou 1 GB

## 6. Accéder à l'interface

Deux URL possibles selon ce qui marche :

- **Direct** : `http://<IP-du-panel>:30500`
- **Via launcher** : clique sur la tuile de l'app sur le launcher Edge → redirige vers la même URL

Tu dois voir l'UI Flask : graphes Chart.js, valeurs T°/débit, état PLC.

---

## Dépannage express

| Symptôme | Cause probable | Action |
|---|---|---|
| App ne démarre pas, status *Failed* | Image non chargée | Vérifie les logs : Apps → ton app → Logs |
| App *Running* mais page blanche au :30500 | Port mal mappé ou pare-feu panel | Vérifie le mapping ports dans la config app |
| Page OK mais "PLC: disconnected" | IP PLC incorrecte ou réseau bloqué | Modifie `PLC_IP`, vérifie le routage panel↔PLC |
| OOM Killed dans les logs | `mem_limit` trop bas | Rebuild avec 768 MB ou 1 GB |
| Logs CSV vides | Volume `logsCSV` non monté | Vérifie la section Storage de la config app |

---

## Si tout casse — rollback

- Apps → ton app → **Stop** puis **Uninstall**
- Tu peux reinstaller le `.app` autant de fois que tu veux, c'est non destructif
- Le volume `logsCSV` est conservé entre installs (sauf si tu fais *Uninstall + delete data*)

---

## Pour itérer après une 1ère install

Si tu dois corriger un truc dans l'app :
1. Modifier le code Flask
2. `docker build -t project-s7-app .`
3. Retourner dans IEAP, ouvrir la version 1.0.0 → **+ New version** (1.0.1)
4. Le compose est conservé, tu changes juste le numéro
5. Export → nouveau `.app` à installer (Edge fait l'update différentiel)
