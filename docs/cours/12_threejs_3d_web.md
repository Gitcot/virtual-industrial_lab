# 12. Three.js — rendu 3D dans le navigateur

## Les 3 objets fondamentaux de toute scène Three.js

```javascript
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 100);
const renderer = new THREE.WebGLRenderer({ antialias: true });
```
- **Scene** : le conteneur de tous les objets 3D (géométries, lumières)
- **Camera** : le point de vue. `PerspectiveCamera(fov, aspect, near, far)`
  — `fov` = champ de vision en degrés, `aspect` = ratio largeur/hauteur,
  `near`/`far` = distances de coupe (rien n'est affiché avant `near` ni
  après `far`, pour des raisons de performance)
- **Renderer** : dessine la scène vue depuis la caméra dans un `<canvas>`,
  en s'appuyant sur WebGL (accélération matérielle GPU)

## Géométrie + Matériau = Mesh

```javascript
const bodyGeometry = new THREE.CylinderGeometry(0.6, 0.6, 1.4, 32);
const bodyMaterial = new THREE.MeshStandardMaterial({ color: getMotorColor("stopped") });
const motorBody = new THREE.Mesh(bodyGeometry, bodyMaterial);
```
- **Geometry** : la forme (ici un cylindre : rayon haut, rayon bas,
  hauteur, nombre de segments radiaux — 32 pour un cylindre bien rond)
- **Material** : comment la surface réagit à la lumière.
  `MeshStandardMaterial` réagit réalistement aux lumières de la scène
  (contrairement à `MeshBasicMaterial` qui ignore l'éclairage)
- **Mesh** : l'assemblage des deux, l'objet réellement ajouté à la scène

## Lumières — indispensables avec `MeshStandardMaterial`

```javascript
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
```
Sans lumière, un `MeshStandardMaterial` apparaît complètement noir —
piège fréquent pour les débutants. `AmbientLight` éclaire uniformément
tout (évite les zones totalement noires), `DirectionalLight` simule une
source lointaine (comme le soleil) qui crée des ombrages directionnels.

## La boucle de rendu (render loop)

```javascript
function animate() {
    requestAnimationFrame(animate);
    rotationAngle += currentRotationSpeed;
    motorBody.rotation.x = rotationAngle;
    renderer.render(scene, camera);
}
animate();
```
`requestAnimationFrame` demande au navigateur d'appeler `animate` juste
avant le prochain rafraîchissement d'écran (typiquement 60 fois/seconde).
C'est ce mécanisme qui crée l'illusion de mouvement continu : à chaque
frame, l'angle de rotation avance un peu, puis la scène est redessinée.

## Le choix pédagogique de ce projet : géométrie procédurale, pas de GLB

`CylinderGeometry` + `BoxGeometry` sont des formes générées par le code,
pas un modèle 3D importé (format GLB/glTF, mentionné dans le master
prompt comme cible finale). C'est un placeholder assumé pour la Phase 5 :
la logique de rendu (couleur selon état, vitesse de rotation) est
identique, qu'on affiche un cylindre ou un vrai modèle de moteur —
remplacer la géométrie plus tard n'impactera pas `motorVisuals.js` ni
`apiClient.js`.

## Import de modèles GLB (pour la suite du projet, non encore implémenté)

```javascript
// Prévu pour une phase ultérieure :
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
const loader = new GLTFLoader();
loader.load("models/moteur_asynchrone.glb", (gltf) => scene.add(gltf.scene));
```
`GLTFLoader` charge un fichier `.glb` (format binaire optimisé pour le
web, compact et rapide à charger — c'est le format cible du master
prompt pour les vrais assets 3D).

## Pour aller plus loin
- Documentation officielle : https://threejs.org/docs/
- "Three.js Journey" (cours approfondi, payant) : https://threejs-journey.com/
