# Client web — Laboratoire moteur (Phase 5)

Client web minimal (HTML + JS modules ES + Three.js via CDN) qui consomme
l'API du laboratoire moteur (Phase 4) et affiche une représentation 3D de
l'état du moteur en temps réel.

## ⚠️ Statut de test — à lire avant utilisation

**Testé réellement (32 tests automatisés, `node --test`) :**
- `src/motorVisuals.js` — logique pure de mapping état→couleur/vitesse de
  rotation/alerte : **14/14 tests passent**
- `src/apiClient.js` — client HTTP vers l'API (avec `fetch` simulé) :
  **6/6 tests passent**, y compris la gestion des erreurs 409/400/500

**NON testé par moi, à vérifier par vous :**
- Le rendu 3D réel dans un navigateur (`src/main.js`, `index.html`). Mon
  environnement d'exécution n'a pas d'accès navigateur/Chromium (le
  téléchargement du binaire est bloqué par la configuration réseau du
  sandbox). J'ai vérifié la syntaxe JS (`node --check`, aucune erreur) et la
  cohérence logique (CORS backend déjà configuré pour ce port), mais **pas
  le rendu visuel lui-même**. C'est la première chose à valider de votre
  côté (voir Guide d'utilisation).

## Géométrie 3D : placeholder assumé

Le moteur est représenté par un cylindre + une boîte (arbre), **pas un vrai
modèle GLB**. C'est une hypothèse de la Phase 5 documentée explicitement,
pas une fonctionnalité cachée comme "finie". Remplacer par un vrai modèle
glTF/GLB optimisé (LOD, textures) est un travail ultérieur (Phase 9, gestion
des packages/assets).

## Structure

```
apps/web/
├── index.html          # page + import map (résout "three" vers un CDN)
├── package.json         # scripts npm (test, dev)
├── src/
│   ├── motorVisuals.js   # logique pure état -> visuel (testée)
│   ├── apiClient.js       # client HTTP vers l'API (testé)
│   └── main.js             # assemble Three.js + apiClient + DOM (non testé automatiquement)
└── tests/
    ├── motorVisuals.test.js
    └── apiClient.test.js
```
