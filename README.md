# Virtual Industrial Lab (VIL) — Core + Laboratoire moteur

Plateforme modulaire de laboratoire industriel virtuel : simulation, pédagogie
technique, IA et jumeau numérique.

Ce dépôt contient le **Core backend** (Phases 1-3) et le **moteur de
simulation du laboratoire moteur** (Phase 4) : authentification (JWT),
modèle Asset extensible (base du futur Digital Twin), machine à états d'un
moteur asynchrone (démarrage direct / étoile-triangle, défauts, thermique),
environnement de développement reproductible.

➡️ **Guide de mise en place complet : voir [`docs/GUIDE_INSTALLATION.md`](docs/GUIDE_INSTALLATION.md)**

➡️ **Cours détaillé sur les technologies utilisées : voir [`docs/cours/00_INDEX.md`](docs/cours/00_INDEX.md)** (14 fichiers, basés sur le code réel du projet)

## Structure du projet

```
virtual-industrial-lab/
├── .devcontainer/          # Environnement reproductible (VS Code / Codespaces)
├── apps/api/                # Backend FastAPI
│   ├── app/
│   │   ├── core/            # config, DB, sécurité, types portables
│   │   ├── models/          # User, Asset, MotorSession
│   │   ├── schemas/         # schémas Pydantic
│   │   ├── services/        # pont MotorSession (DB) <-> MotorSimulator (pur)
│   │   └── api/routes/      # endpoints (auth, assets, simulation)
│   ├── alembic/              # migrations de base de données
│   ├── tests/                 # tests d'intégration API (pytest) — 25/25 passent
│   ├── requirements.txt
│   └── .env.example          # copier en .env dans ce même dossier
├── simulation/               # Moteur de simulation PUR (Phase 4-5), testable seul
│   ├── motor_engine.py         # machine à états du moteur asynchrone
│   ├── motor_physics.py         # théorie du circuit équivalent, formule de Kloss — testé 15/15
│   ├── frame_dimensions.py       # correspondance puissance -> carcasse IEC 60072 — testé 7/7
│   └── tests/
├── tools/
│   ├── blender_motor_generator.py  # génère un GLB paramétrique via bpy (Blender headless)
│   └── tests/                        # lance réellement Blender, valide les GLB — 5/5
├── apps/web/                 # Client web 3D (Phase 5)
│   ├── index.html             # page + import map Three.js (CDN) + GLTFLoader
│   ├── src/
│   │   ├── motorVisuals.js     # logique pure état -> visuel — testée 14/14
│   │   ├── apiClient.js         # client HTTP -> API — testé 10/10
│   │   └── main.js               # scène 3D + chargement GLB réel + DOM (non testable en sandbox)
│   └── tests/
├── packages/                # (Phase 9) Labs distribués en packages versionnés
├── labs/                     # (Phase 14) laboratoires pédagogiques futurs
├── docs/
│   ├── GUIDE_INSTALLATION.md
│   └── cours/                # 16 fichiers de cours sur les technos utilisées
└── docker-compose.yml
```

## État d'avancement (roadmap du master prompt)

| Phase | Contenu | Statut |
|---|---|---|
| 0 | Architecture cible | ✅ Fait |
| 1 | Git, devcontainer, qualité de code | ✅ Fait |
| 2 | Core, config, DB, migrations | ✅ Fait |
| 3 | FastAPI, auth, autorisation, validation | ✅ Fait |
| 4 | Moteur d'état + simulation du moteur électrique | ✅ Fait |
| 5 | 3D optimisée, assets, LOD, cache | 🟡 Base fonctionnelle (voir détail ci-dessous) |
| 6 | Mesures et instruments virtuels avancés | ⏳ À construire (base posée en Phase 4) |
| 7 | Scénarios de TP, évaluation/scoring | ⏳ À construire |
| 8 | Offline-first, sync, Network Quality Manager | ⏳ À construire |
| 9-11 | Packages/Labs, CI/CD, observabilité, déploiement | ⏳ À construire |
| 12-14 | IA/OCR, Digital Twin calibré, nouveaux laboratoires | ⏳ À construire |

**Pourquoi les Phases 5+ ne sont pas encore codées** : elles nécessitent des
choix techniques non tranchés (moteur 3D web ? quels modèles GLB ? cadence de
sync offline ?) qui doivent être validés avec vous avant d'écrire du code
potentiellement à refaire. Le Core et le laboratoire moteur backend sont une
base stable sur laquelle ces phases peuvent s'appuyer sans réécriture.

## Détail Phase 5 (3D) — ce qui est fait, ce qui ne l'est pas

- **Fait et testé** : logique de mapping état→visuel (couleur, vitesse de
  rotation, alerte pulsée, overlay thermique) — 14/14 tests. Client HTTP
  vers l'API — 10/10 tests, y compris gestion d'erreurs.
- **Fait, non testé automatiquement** : la scène 3D elle-même
  (`apps/web/main.js`) et le rendu dans un navigateur. Mon environnement de
  développement n'a pas d'accès à un navigateur/Chromium (téléchargement
  bloqué par la configuration réseau du sandbox) — je ne peux donc pas
  vérifier visuellement que la scène s'affiche correctement. **À valider en
  premier de votre côté** (voir `docs/GUIDE_INSTALLATION.md`, section
  client web).
- **Hypothèse assumée** : géométrie 3D procédurale simple (cylindre +
  boîte) en l'absence de vrai modèle GLB du moteur. Pas un modèle
  pédagogique fini, un placeholder fonctionnel.

## Modèle physique du moteur + génération 3D réelle (au-delà de la Phase 5 initiale)

À la demande explicite de l'utilisateur, deux volets ont été ajoutés :

**1. Théorie électromagnétique du moteur asynchrone** (`simulation/motor_physics.py`)
- Circuit équivalent, vitesse de synchronisme (Ns=120f/p), glissement,
  formule de Kloss pour la courbe couple-vitesse
- Paramétrable depuis une vraie plaque signalétique (puissance, pôles,
  vitesse nominale si connue)
- **Théorie établie, PAS les courbes d'essai propriétaires d'un
  constructeur précis** — voir le docstring de `motor_physics.py` pour le
  détail du statut épistémique de chaque valeur (mesurée vs estimée)
- 15/15 tests, vérifiés contre des faits théoriques connus (ex: 4 pôles/50Hz
  → 1500 tr/min)

**2. Génération 3D paramétrique via l'API Blender (`bpy`)** (`tools/blender_motor_generator.py`)
- Géométrie procédurale (corps, ailettes de refroidissement, arbre, boîte
  à bornes, pattes) dimensionnée automatiquement
- Dimensions dérivées soit de cotes constructeur réelles (si fournies dans
  `Asset.geometry`), soit d'une estimation IEC 60072 depuis la puissance
  (`simulation/frame_dimensions.py`, 7/7 tests)
- **Blender a été installé et testé dans l'environnement de développement**
  (pas seulement écrit en théorie) : 5/5 tests qui lancent réellement
  Blender en sous-processus et valident les GLB produits avec `pygltflib`,
  y compris une vérification dimensionnelle exacte au millimètre près
- Intégré à l'API (`POST /api/assets/{id}/generate-3d-model`,
  `GET .../motor-physics`, `GET .../3d-model`) — 7/7 tests d'intégration,
  dont un test de bout en bout réel (API → sous-processus Blender → GLB
  téléchargé → validé structurellement)
- Client web mis à jour pour charger le vrai GLB via `GLTFLoader`
  (remplace le placeholder procédural quand un Asset est associé) — **non
  vérifié visuellement** (même limite que le reste de la Phase 5, voir
  ci-dessus)

**Total : 90 tests automatisés passent** sur l'ensemble du projet
(36 simulation + 5 Blender + 25 API + 24 JS).

## Ce qui a été réellement testé (pas juste écrit) — détail Phases 1-4

- **32/32 tests automatisés** à la fin de la Phase 4 (14 moteur pur + 18 API)
- **Migration Alembic** régénérée et appliquée avec succès (tables `users`,
  `assets`, `motor_sessions`)
- **Test HTTP de bout en bout réel** (curl, pas de mock) : inscription →
  connexion → création de session → démarrage direct → observation du
  courant d'appel (20.8A, soit 6.5× le nominal 3.2A) pendant le régime
  transitoire → chute à 3.2A une fois en régime nominal → **persistance
  vérifiée après un redémarrage complet du serveur** → injection de défaut
  électrique → tentative d'arrêt refusée (HTTP 409, comportement attendu) →
  réarmement → retour à l'arrêt propre.
- **3 bugs réels trouvés et corrigés en Phase 2-3** (types Postgres-only
  incompatibles SQLite, version bcrypt cassée, imports Alembic manquants).
- **2 bugs réels trouvés et corrigés en Phase 4** : le courant restait basé
  sur l'état précédent juste après une transition (mesure périmée) ; la
  constante de temps thermique (45s) était irréaliste et déclenchait un
  arrêt thermique dès un démarrage normal de quelques secondes — corrigée à
  300s (~5 min), documentée comme hypothèse pédagogique à calibrer plus tard
  avec de vraies données (Phase 12-13, Digital Twin).
