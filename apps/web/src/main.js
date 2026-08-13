import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createApiClient, ApiError } from "./apiClient.js";
import { getMotorColor, getRotationSpeed, shouldPulseAlert, temperatureToHeatOverlay } from "./motorVisuals.js";

// Représentation 3D : deux modes possibles.
// 1. Modèle GLB réel généré par Blender depuis une plaque signalétique
//    (tools/blender_motor_generator.py, via l'API /api/assets/{id}/3d-model)
//    — utilisé si l'utilisateur associe la session à un Asset.
// 2. Géométrie procédurale simple (cylindre + boîte) en repli, si aucun
//    Asset n'est associé ou si le chargement du GLB échoue.
// ⚠️ Le chargement GLB n'a pas pu être testé visuellement dans mon
// environnement (pas de navigateur disponible) — voir apps/web/README.md.

const API_BASE_URL = window.VIL_API_BASE_URL || "https://upgraded-space-bassoon-57rpj957vp42757w-8000.app.github.dev";
const api = createApiClient(API_BASE_URL);

let currentSessionId = null;
let pollTimer = null;

// ---------- Scène 3D ----------

const container = document.getElementById("scene-container");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1115);

const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 100);
camera.position.set(3, 2, 4);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(5, 5, 5);
scene.add(dirLight);

// Corps du moteur : par défaut, placeholder procédural (cylindre). Peut
// être remplacé dynamiquement par un vrai modèle GLB via loadRealMotorModel().
const bodyGeometry = new THREE.CylinderGeometry(0.6, 0.6, 1.4, 32);
const bodyMaterial = new THREE.MeshStandardMaterial({ color: getMotorColor("stopped") });
const motorBody = new THREE.Mesh(bodyGeometry, bodyMaterial);
motorBody.rotation.z = Math.PI / 2;
scene.add(motorBody);

let realModelRoot = null; // racine du modèle GLB chargé, si présent
const gltfLoader = new GLTFLoader();

/**
 * Tente de charger le modèle GLB réel généré par Blender pour cet Asset
 * (voir POST /api/assets/{id}/generate-3d-model côté API). En cas
 * d'échec (pas encore généré, erreur réseau...), conserve le placeholder
 * procédural existant plutôt que de casser l'affichage.
 */
async function loadRealMotorModel(assetId) {
  const url = `${API_BASE_URL}/api/assets/${assetId}/3d-model`;
  try {
    const gltf = await gltfLoader.loadAsync(url, undefined, undefined);
    // Le modèle Blender est en mètres, orienté axe X (voir blender_motor_generator.py)
    if (realModelRoot) scene.remove(realModelRoot);
    realModelRoot = gltf.scene;
    scene.add(realModelRoot);
    motorBody.visible = false; // masque le placeholder, garde la logique de couleur/rotation active
    log("Modèle 3D réel chargé (généré par Blender).");
  } catch (e) {
    log(`Modèle 3D réel indisponible (${e.message || e}), utilisation du placeholder.`);
  }
}

// Arbre moteur (pour visualiser la rotation)
const shaftGeometry = new THREE.BoxGeometry(0.1, 0.1, 1.6);
const shaftMaterial = new THREE.MeshStandardMaterial({ color: 0xcfd8dc });
const shaft = new THREE.Mesh(shaftGeometry, shaftMaterial);
scene.add(shaft);

let rotationAngle = 0;
let currentRotationSpeed = 0;
let pulseActive = false;
let pulseClock = 0;

function animate() {
  requestAnimationFrame(animate);
  rotationAngle += currentRotationSpeed;
  motorBody.rotation.x = rotationAngle;
  shaft.rotation.x = rotationAngle;
  if (realModelRoot) {
    realModelRoot.rotation.x = rotationAngle;
  }

  if (pulseActive) {
    pulseClock += 0.1;
    const pulse = (Math.sin(pulseClock) + 1) / 2; // 0..1
    bodyMaterial.emissive = new THREE.Color(0xff0000);
    bodyMaterial.emissiveIntensity = pulse * 0.6;
  } else {
    bodyMaterial.emissiveIntensity = 0;
  }

  renderer.render(scene, camera);
}
animate();

function applyMotorVisuals(session) {
  bodyMaterial.color.setHex(getMotorColor(session.state));
  currentRotationSpeed = getRotationSpeed(session.state);
  pulseActive = shouldPulseAlert(session.state);
}

// ---------- UI / mesures ----------

function log(message) {
  const el = document.getElementById("log");
  const line = document.createElement("div");
  line.textContent = `${new Date().toLocaleTimeString()} — ${message}`;
  el.prepend(line);
}

function updateMeasurementsPanel(session) {
  document.getElementById("status-badge").textContent = `état: ${session.state}`;
  document.getElementById("m-voltage").textContent = session.voltage_v.toFixed(1);
  document.getElementById("m-current").textContent = session.current_a.toFixed(2);
  document.getElementById("m-temp").textContent = session.simulated_temp_c.toFixed(1);
  document.getElementById("m-fault").textContent = session.fault_active || "—";
  applyMotorVisuals(session);
}

async function handleAction(actionFn) {
  if (!currentSessionId) {
    log("Créez d'abord une session.");
    return;
  }
  try {
    const session = await actionFn();
    updateMeasurementsPanel(session);
    log(`OK -> état: ${session.state}`);
  } catch (e) {
    if (e instanceof ApiError) {
      log(`Erreur ${e.status}: ${e.detail}`);
    } else {
      log(`Erreur: ${e.message}`);
    }
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    if (!currentSessionId) return;
    try {
      const session = await api.tickSession(currentSessionId, 0.5);
      updateMeasurementsPanel(session);
    } catch (e) {
      // une erreur de tick (ex: état arrêté) n'est pas bloquante pour le polling
    }
  }, 500);
}

// ---------- Câblage des boutons ----------

document.getElementById("btn-create-asset-and-model").addEventListener("click", async () => {
  const statusEl = document.getElementById("asset-status");
  try {
    const power = parseFloat(document.getElementById("np-power").value);
    const poles = parseInt(document.getElementById("np-poles").value, 10);
    const speed = parseFloat(document.getElementById("np-speed").value);
    const voltage = parseFloat(document.getElementById("np-voltage").value);
    const current = parseFloat(document.getElementById("np-current").value);

    statusEl.textContent = "Création de l'Asset...";
    const asset = await api.createAsset({
      name: `Moteur ${power}kW / ${poles}p`,
      electrical_properties: {
        rated_power_kw: power,
        rated_voltage_v: voltage,
        rated_current_a: current,
        frequency_hz: 50.0,
      },
      mechanical_properties: { poles, rated_speed_rpm: speed },
    });
    log(`Asset créé: ${asset.id}`);

    statusEl.textContent = "Génération du modèle 3D (Blender, quelques secondes)...";
    const genResult = await api.generate3DModel(asset.id);
    log(`Modèle 3D généré (${genResult.file_size_bytes} octets).`);

    statusEl.textContent = "Calcul de la physique du moteur...";
    const physics = await api.getMotorPhysics(asset.id);
    log(
      `Physique: Ns=${physics.synchronous_speed_rpm}tr/min, glissement=${physics.rated_slip} (${physics.rated_slip_source}), couple nominal=${physics.rated_torque_nm}N.m`
    );

    await loadRealMotorModel(asset.id);

    // Crée aussi une session de simulation liée à cet asset
    const session = await api.createSession({ asset_id: asset.id });
    currentSessionId = session.id;
    updateMeasurementsPanel(session);
    startPolling();

    statusEl.textContent = `Prêt (asset ${asset.id.slice(0, 8)}...)`;
  } catch (e) {
    statusEl.textContent = "Échec";
    log(`Erreur génération asset/modèle: ${e.message}`);
  }
});

document.getElementById("btn-login").addEventListener("click", async () => {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  try {
    await api.registerAndLogin(email, password);
    document.getElementById("auth-status").textContent = `connecté: ${email}`;
    log("Connecté.");
  } catch (e) {
    log(`Échec connexion: ${e.message}`);
  }
});

document.getElementById("btn-create-session").addEventListener("click", async () => {
  try {
    const session = await api.createSession({});
    currentSessionId = session.id;
    updateMeasurementsPanel(session);
    log(`Session créée: ${session.id}`);
    startPolling();
  } catch (e) {
    log(`Échec création session: ${e.message}`);
  }
});

document.getElementById("btn-start-direct").addEventListener("click", () =>
  handleAction(() => api.startSession(currentSessionId, "direct"))
);
document.getElementById("btn-start-star").addEventListener("click", () =>
  handleAction(() => api.startSession(currentSessionId, "star_delta"))
);
document.getElementById("btn-stop").addEventListener("click", () =>
  handleAction(() => api.stopSession(currentSessionId))
);
document.getElementById("btn-fault-thermal").addEventListener("click", () =>
  handleAction(() => api.injectFault(currentSessionId, "thermal_overload"))
);
document.getElementById("btn-fault-electrical").addEventListener("click", () =>
  handleAction(() => api.injectFault(currentSessionId, "phase_loss"))
);
document.getElementById("btn-reset").addEventListener("click", () =>
  handleAction(() => api.resetSession(currentSessionId))
);
document.getElementById("btn-ack").addEventListener("click", () =>
  handleAction(() => api.acknowledgeSession(currentSessionId))
);
