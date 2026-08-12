# Guide d'installation — Virtual Industrial Lab (Core backend)

## 1. Prérequis à installer sur votre machine

| Outil | Version | Vérifier avec |
|---|---|---|
| Git | récente | `git --version` |
| Docker Desktop (ou Engine) | récente | `docker --version` |
| Python | 3.11+ | `python3 --version` |
| Compte GitHub | — | — |
| VS Code (recommandé) | récente | — |

## 2. Deux façons de démarrer

### Option A — GitHub Codespaces (recommandé, zéro installation locale)

1. Créez un dépôt GitHub vide et poussez ce dossier dedans :
   ```bash
   cd virtual-industrial-lab
   git init
   git add .
   git commit -m "Core: auth + assets + migrations"
   git branch -M main
   git remote add origin https://github.com/<votre-user>/virtual-industrial-lab.git
   git push -u origin main
   ```
2. Sur GitHub : bouton **Code → Codespaces → Create codespace on main**.
3. L'environnement se construit automatiquement (`.devcontainer/devcontainer.json`
   installe Python 3.11 et les dépendances). Passez directement à l'étape 4.

### Option B — En local

```bash
cd virtual-industrial-lab
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
cd apps/api
pip install -r requirements.txt
```

⚠️ **Point de vigilance testé et corrigé** : `bcrypt` doit rester en version
`4.0.1` (déjà pinné dans `requirements.txt`). Les versions plus récentes
cassent la compatibilité avec `passlib` (erreur `module 'bcrypt' has no
attribute '__about__'`). Ne mettez pas à jour `bcrypt` seul sans re-tester.

## 3. Configuration de l'environnement

⚠️ Le fichier `.env` doit être créé **dans `apps/api/`** (c'est là que
l'application le lit), pas à la racine du projet.

```bash
cd apps/api
cp .env.example .env
```
Éditez `apps/api/.env` et changez au minimum `SECRET_KEY` (une vraie valeur
aléatoire, jamais celle par défaut) :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Collez le résultat dans `.env` → `SECRET_KEY=...`

## 4. Démarrer la base de données PostgreSQL

Depuis la racine du projet :
```bash
docker compose up -d
```
Vérifiez qu'elle tourne :
```bash
docker compose ps
```

## 5. Appliquer les migrations (créer les tables)

Depuis `apps/api/` :
```bash
python -m alembic upgrade head
```
Résultat attendu : `Running upgrade -> ..., initial schema` sans erreur.

## 6. Lancer l'API

Depuis `apps/api/` :
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Documentation interactive : http://localhost:8000/docs
- Vérification santé : http://localhost:8000/api/health → `{"status":"ok",...}`

## 7. Lancer les tests automatisés

Deux suites de tests indépendantes :

**Tests du moteur de simulation pur** (aucune dépendance DB/API), depuis la
racine du projet :
```bash
python -m pytest simulation/tests/ -v
```
Résultat attendu : **14 passed**.

**Tests d'intégration API** (auth, assets, laboratoire moteur), depuis
`apps/api/` :
```bash
pytest -v
```
Résultat attendu : **18 passed**. Ces tests couvrent : inscription, doublons
d'email, connexion, mot de passe erroné, protection des routes par JWT,
création/lecture d'Asset, et tout le cycle de vie d'une session de
simulation moteur (démarrage direct/étoile-triangle, courant d'appel,
injection de défaut, refus d'arrêt pendant un défaut, réarmement, isolation
des sessions par utilisateur).

## 8. Créer une nouvelle migration après modification d'un modèle

Chaque fois que vous modifiez un fichier dans `app/models/` :
```bash
python -m alembic revision --autogenerate -m "description du changement"
python -m alembic upgrade head
```
Vérifiez toujours le contenu du fichier généré dans `alembic/versions/`
avant de l'appliquer en production.

## 9. Tester rapidement l'API avec curl

```bash
# Inscription
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"vous@exemple.com","password":"motdepasse123"}'

# Connexion (récupère un token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"vous@exemple.com","password":"motdepasse123"}'

# Route protégée (remplacez TOKEN)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer TOKEN"
```

## 9bis. Tester le laboratoire moteur (Phase 4) avec curl

```bash
# Créer une session de simulation (remplacez TOKEN)
SID=$(curl -s -X POST http://localhost:8000/api/simulation/sessions \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# Démarrage direct
curl -X POST http://localhost:8000/api/simulation/sessions/$SID/start \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"mode":"direct"}'

# Faire avancer la simulation de 0.5s (répéter plusieurs fois pour voir le
# courant d'appel ~20.8A chuter à 3.2A une fois "running")
curl -X POST http://localhost:8000/api/simulation/sessions/$SID/tick \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"dt_seconds":0.5}'

# Provoquer un défaut (thermal_overload | phase_loss)
curl -X POST http://localhost:8000/api/simulation/sessions/$SID/fault \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"fault_type":"phase_loss"}'

# Réarmer puis revenir à l'arrêt
curl -X POST http://localhost:8000/api/simulation/sessions/$SID/reset \
  -H "Authorization: Bearer TOKEN"
curl -X POST http://localhost:8000/api/simulation/sessions/$SID/acknowledge \
  -H "Authorization: Bearer TOKEN"
```

Endpoints complets : `POST /start` (mode: direct|star_delta), `POST /stop`,
`POST /fault` (fault_type: thermal_overload|phase_loss), `POST /reset`,
`POST /acknowledge`, `POST /tick` (dt_seconds), `GET /{id}`, `GET` (liste).

## 10. Erreurs fréquentes

| Symptôme | Cause probable | Solution |
|---|---|---|
| `could not translate host name "db"` | L'API tourne hors Docker mais pointe vers le nom de service Docker `db` | En local hors Docker, changez `DATABASE_URL` dans `apps/api/.env` pour `localhost` au lieu de `db` |
| `module 'bcrypt' has no attribute '__about__'` | Version de `bcrypt` trop récente | `pip install bcrypt==4.0.1` |
| `no such table: users` | Migrations non appliquées | `python -m alembic upgrade head` |
| Port 8000 déjà utilisé | Autre process dessus | `uvicorn app.main:app --port 8001` |

## 11. Client web 3D (Phase 5)

⚠️ Cette partie n'a **pas** pu être testée visuellement par moi (pas
d'accès navigateur dans mon environnement). Suivez ces étapes et vérifiez
vous-même que ça fonctionne — c'est la première validation attendue.

**Installer les tests JS** (aucune dépendance à télécharger, Node 18+
suffit avec son test runner intégré) :
```bash
cd apps/web
node --test tests/*.test.js
```
Résultat attendu : **20 passed** (14 pour la logique visuelle, 6 pour le
client API).

**Lancer le client web** (nécessite que l'API tourne déjà sur le port 8000,
cf. étape 6) :
```bash
cd apps/web
python3 -m http.server 5173
```
Ouvrez ensuite **http://localhost:5173** dans un navigateur. Vous devriez
voir :
- Une scène 3D avec un cylindre gris (moteur à l'arrêt)
- Un formulaire connexion/inscription pré-rempli
- Des boutons pour créer une session, démarrer (direct/étoile-triangle),
  provoquer un défaut, réarmer

**Test manuel à faire** : connexion → nouvelle session → démarrer (direct)
→ le cylindre doit passer à l'orange et commencer à tourner sur son axe →
après quelques secondes, passer au vert (régime nominal) → les mesures
(tension/courant/température) doivent se mettre à jour en direct dans le
panneau sous la scène.

**Si ça ne fonctionne pas** : ouvrez la console développeur du navigateur
(F12) et regardez les erreurs. Cause probable n°1 : l'API n'est pas lancée
ou tourne sur un autre port — vérifiez `API_BASE_URL` dans
`apps/web/src/main.js` (par défaut `http://localhost:8000`).

## 12. Génération 3D paramétrique via Blender (moteur réel depuis plaque signalétique)

Cette fonctionnalité génère un vrai modèle 3D (.glb) dimensionné à partir
d'une plaque signalétique réelle (puissance, pôles, vitesse...), en
utilisant l'API Python de Blender (`bpy`) en mode headless (sans interface
graphique).

### Installer Blender (Linux/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y blender --no-install-recommends
```

⚠️ **Problème rencontré et corrigé pendant le développement** : sur une
image Ubuntu avec un cache apt légèrement désynchronisé, l'installation
peut échouer avec des erreurs `404 Not Found` sur des dépendances
(`libpq5`, `libmysqlclient21`, `libgphoto2-*`). Si ça arrive :
```bash
sudo apt-get update              # resynchronise les index de paquets
sudo apt-get install -y blender --no-install-recommends --fix-missing
sudo apt-get --fix-broken install -y   # répare les dépendances cassées restantes
```

Vérifier l'installation :
```bash
blender --version
blender --background --python-expr "import bpy; print('OK', bpy.app.version_string)"
```
Résultat attendu : `Blender 4.x.x` puis `OK 4.x.x` sans erreur.

**Sur macOS** : `brew install --cask blender` puis ajouter
`/Applications/Blender.app/Contents/MacOS` au PATH.
**Sur Windows** : télécharger l'installeur depuis blender.org, puis
ajouter le dossier d'installation au PATH.

### Tester le générateur directement (sans passer par l'API)

```bash
cd apps/api && pip install -r requirements.txt   # inclut pygltflib pour la validation
cd ../..
blender --background --python tools/blender_motor_generator.py -- \
  --shaft-height 90 --body-diameter 150 --body-length 230 \
  --shaft-diameter 24 --shaft-length 50 \
  --output /tmp/moteur_test.glb
```
Résultat attendu : `OK: moteur exporté vers /tmp/moteur_test.glb`. Le
fichier peut être ouvert dans n'importe quel visualiseur GLB (y compris
https://gltf-viewer.donmccurdy.com/ en ligne) pour vérification visuelle.

### Lancer les tests du générateur

```bash
python -m pytest tools/tests/ -v
```
Résultat attendu : **5 passed** — ces tests lancent réellement Blender
(quelques secondes chacun) et valident les fichiers GLB produits avec
`pygltflib`, y compris la vérification que les dimensions générées
correspondent exactement (au mm près) aux paramètres demandés.

### Utiliser la génération 3D via l'API (depuis une plaque signalétique réelle)

```bash
# 1. Créer un Asset avec les données de plaque signalétique
ASSET_ID=$(curl -s -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "Moteur atelier 1",
    "electrical_properties": {"rated_power_kw": 1.5, "rated_voltage_v": 400, "rated_current_a": 3.2, "frequency_hz": 50},
    "mechanical_properties": {"poles": 4, "rated_speed_rpm": 1450}
  }' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 2. Calculer la physique du moteur (théorie du circuit équivalent)
curl -s http://localhost:8000/api/assets/$ASSET_ID/motor-physics -H "Authorization: Bearer TOKEN"

# 3. Générer le modèle 3D (lance Blender, quelques secondes)
curl -s -X POST http://localhost:8000/api/assets/$ASSET_ID/generate-3d-model -H "Authorization: Bearer TOKEN"

# 4. Télécharger le modèle généré
curl -s http://localhost:8000/api/assets/$ASSET_ID/3d-model -H "Authorization: Bearer TOKEN" -o moteur.glb
```

**Pour utiliser des cotes constructeur réelles** (au lieu de l'estimation
IEC 60072 automatique), ajouter un champ `geometry` à la création de
l'Asset :
```json
"geometry": {
  "frame_designation": "90S",
  "shaft_height_mm": 90, "body_diameter_mm": 150, "body_length_mm": 230,
  "shaft_diameter_mm": 24, "shaft_length_mm": 50
}
```

### ⚠️ Statut de test du chargement dans le client web

Le client web (`apps/web/src/main.js`) tente de charger le vrai GLB
généré (bouton "Créer Asset + générer modèle 3D réel"). Comme pour le
reste de la Phase 5, **je n'ai pas pu vérifier visuellement dans un
navigateur** que le modèle s'affiche correctement une fois chargé — le
code est syntaxiquement valide et les appels API sous-jacents sont
testés, mais le rendu final reste à valider par vous.

## 13. Prochaine étape (Phase 6)

Une fois le client web validé de votre côté (retour attendu : ça marche /
ça ne marche pas + captures d'écran ou messages d'erreur si besoin), la
suite logique est la **Phase 6 (instruments virtuels avancés + scénarios de
TP)**, qui s'appuiera sur ce qui existe déjà.
