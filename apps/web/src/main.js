import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createApiClient } from "./apiClient.js";

const API_BASE_URL = window.VIL_API_BASE_URL;
const api = createApiClient(API_BASE_URL);

let currentAssetId = null; 
let currentSessionId = null;
let pollTimer = null;

// ==========================================
// DRAG & DROP OSCILLOSCOPE (Nouveau !)
// ==========================================
const oscPanel = document.getElementById("oscilloscope-panel");
const oscHeader = document.getElementById("osc-header");
let isDraggingOsc = false, offsetX = 0, offsetY = 0;

oscHeader.addEventListener('mousedown', (e) => {
    isDraggingOsc = true;
    const rect = oscPanel.getBoundingClientRect();
    offsetX = e.clientX - rect.left;
    offsetY = e.clientY - rect.top;
});
document.addEventListener('mousemove', (e) => {
    if (!isDraggingOsc) return;
    oscPanel.style.left = (e.clientX - offsetX) + 'px';
    oscPanel.style.top = (e.clientY - offsetY) + 'px';
    oscPanel.style.bottom = 'auto'; // Désactive le placement par le bas
    oscPanel.style.right = 'auto';
});
document.addEventListener('mouseup', () => { isDraggingOsc = false; });

// ==========================================
// EVENTS D'INTERFACE BASIQUES (Sliders)
// ==========================================
document.getElementById('kt1-timer').addEventListener('input', (e) => document.getElementById('kt1-val').innerText = e.target.value + 's');
document.getElementById('meter-mode').addEventListener('change', (e) => {
    document.getElementById('meg-options').style.display = (e.target.value === 'MEG') ? 'block' : 'none';
    document.getElementById('meter-display').innerText = '---';
});

// ==========================================
// MOTEUR AUDIO
// ==========================================
const AudioContext = window.AudioContext || window.webkitAudioContext;
let audioCtx;
function initAudio() { if (!audioCtx) audioCtx = new AudioContext(); if (audioCtx.state === 'suspended') audioCtx.resume(); }
document.body.addEventListener('click', initAudio, { once: true });

function playSound(type) {
    if (!audioCtx) return; const t = audioCtx.currentTime; const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    if (type === 'contactor_on') { osc.type = 'square'; osc.frequency.setValueAtTime(100, t); osc.frequency.exponentialRampToValueAtTime(20, t + 0.1); gain.gain.setValueAtTime(0.8, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1); osc.start(t); osc.stop(t + 0.1); }
    else if (type === 'contactor_off') { osc.type = 'square'; osc.frequency.setValueAtTime(80, t); osc.frequency.exponentialRampToValueAtTime(10, t + 0.1); gain.gain.setValueAtTime(0.5, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1); osc.start(t); osc.stop(t + 0.1); }
    else if (type === 'error') { osc.type = 'sawtooth'; osc.frequency.setValueAtTime(150, t); osc.frequency.linearRampToValueAtTime(100, t + 0.3); gain.gain.setValueAtTime(0.3, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.3); osc.start(t); osc.stop(t + 0.3); }
    else if (type === 'fault') { playSound('contactor_off'); osc.type = 'square'; osc.frequency.setValueAtTime(500, t); osc.frequency.setValueAtTime(600, t + 0.2); osc.frequency.setValueAtTime(500, t + 0.4); gain.gain.setValueAtTime(0.15, t); gain.gain.linearRampToValueAtTime(0.01, t + 1.0); osc.start(t); osc.stop(t + 1.0); }
    else if (type === 'loto') { osc.type = 'triangle'; osc.frequency.setValueAtTime(800, t); osc.frequency.exponentialRampToValueAtTime(200, t + 0.1); gain.gain.setValueAtTime(0.3, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1); osc.start(t); osc.stop(t + 0.1); }
    else if (type === 'megger') { osc.type = 'sine'; osc.frequency.setValueAtTime(2000, t); gain.gain.setValueAtTime(0.1, t); gain.gain.linearRampToValueAtTime(0.0, t + 0.5); osc.start(t); osc.stop(t + 0.5); }
}

// ==========================================
// SCÈNE 3D
// ==========================================
const container = document.getElementById("scene-container");
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(2.5, 1.8, 3.2);

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
container.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const dirLight = new THREE.DirectionalLight(0xffffff, 1.2); dirLight.position.set(3, 5, 4); dirLight.castShadow = true; scene.add(dirLight);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(15, 15), new THREE.MeshStandardMaterial({ color: 0x1a1c22 })); floor.rotation.x = -Math.PI / 2; floor.position.y = -0.6; floor.receiveShadow = true; scene.add(floor);

window.addEventListener('resize', () => { camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); });

// ==========================================
// MODÈLE PHYSIQUE INDUSTRIEL
// ==========================================
let realModelRoot = null; let statorMaterial = null;
let motorConfig = { P_kw: 11, poles: 4, Ns: 1500, Nn: 1450, In: 22.0, loadType: 'pump_fan' };
let motorPhys = { rpm: 0, current_true: 0, temp: 20.0 };
let meterDisplayCurrent = 0; let rotationAngle = 0;
let currentSessionState = "stopped"; let currentFault = null; 
let lotoState = 0; let doorOpen = false; let coverOpen = false; let probes = []; let securityAlertTimer = 0;
let currentStartMode = "direct_star"; let timeInRunPhase = 0; let lastTime = performance.now();
let timer_KT1 = 4.0; 

const oscCanvas = document.getElementById('osc-canvas');
const oscCtx = oscCanvas.getContext('2d');
let oscDataI = []; let oscDataN = [];

function updateMotorSpecs() {
    motorConfig.P_kw = parseFloat(document.getElementById("np-power").value) || 11.0;
    motorConfig.poles = parseInt(document.getElementById("np-poles").value) || 4;
    motorConfig.loadType = document.getElementById("load-type").value;
    motorConfig.Ns = (120 * 50) / motorConfig.poles; motorConfig.Nn = motorConfig.Ns * 0.96; motorConfig.In = motorConfig.P_kw * 1.85; 
    document.getElementById("dim-f1").value = motorConfig.In.toFixed(1);
    document.getElementById("dim-q1").value = (motorConfig.In * 1.2).toFixed(1);
}

// ==========================================
// SYSTÈME EXPERT & SÉCURITÉ
// ==========================================
function triggerSmartFault(type, customTitle=null, customLesson=null) {
    if(currentFault) return; playSound('fault'); currentFault = type;
    let title = customTitle || "🛑 DÉCLENCHEMENT SÉCURITÉ"; let symptom = "Le système s'est mis en sécurité."; let hint = "Analysez les paramètres."; let lesson = customLesson || "Erreur de dimensionnement ou de paramétrage.";
    
    if (type === "thermal_trip" && !customTitle) {
        title = "🛑 DÉCLENCHEMENT THERMIQUE (F1)"; symptom = "Arrêt net du moteur. Température critique (I²t dépassé).";
        if (currentStartMode === "star_delta" && timer_KT1 < 4.0) {
             hint = `Temporisateur KT1 (${timer_KT1}s) commuté trop tôt !`; lesson = `Passage en Triangle avant la fin de l'accélération = Pic de courant mortel.\n\n🛠️ ACTION : Augmentez KT1 à 6-8s.`;
        } else {
             hint = "Surcharge ou inertie trop forte."; lesson = `Le relais thermique F1 a fondu car le courant est resté supérieur à son réglage trop longtemps.\n\n🛠️ ACTION : Adaptez le démarrage ou augmentez la Puissance.`;
        }
    }
    
    document.getElementById("lm-title").innerText = title; document.getElementById("lm-symptom").innerText = symptom;
    document.getElementById("lm-hint").innerText = hint; document.getElementById("lm-lesson").innerText = lesson;
    document.getElementById("lesson-modal").style.display = "block"; log(`💥 EXPERTISE : ${title}`);
}

function triggerSecurityAlert(msg) { playSound('error'); log(msg); securityAlertTimer = 180; }

function addProbe(terminalName) {
    if (probes.length >= 2) probes.shift();
    if (!probes.includes(terminalName)) probes.push(terminalName);
    document.getElementById("probe-status").innerText = `Sondes branchées : [ ${probes.join(" | ")} ]`; evaluateMeasurement();
}

document.getElementById("btn-clear-probes").addEventListener("click", () => {
    probes = []; document.getElementById("probe-status").innerText = `Sondes branchées : (Aucune)`; document.getElementById("meter-display").innerText = "0.00"; log("🔌 Sondes retirées.");
});

function checkProbesSafety() {
    if (probes.length > 0) { triggerSecurityAlert("❌ SÉCURITÉ : Retirez TOUTES les sondes de mesure (Bouton Orange) avant de manipuler l'installation !"); return false; }
    return true;
}

// ==========================================
// SCÈNE 3D & RAYCASTER
// ==========================================
async function loadRealMotorModel(assetId) {
  const url = `${API_BASE_URL}/api/assets/${assetId}/3d-model?cb=${Date.now()}`;
  const gltf = await new GLTFLoader().loadAsync(url);
  if (realModelRoot) scene.remove(realModelRoot); realModelRoot = gltf.scene;
  const startType = document.getElementById("start-type").value; 
  realModelRoot.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true; child.receiveShadow = true;
      if (child.name === "Stator") statorMaterial = child.material;
      if (child.name === "Padlock") child.visible = false;
      if (child.name === "Contactor_KM2" || child.name === "Contactor_KM3" || child.name === "Timer_Relay") child.visible = (startType === "star_delta");
      if (child.name === "Link_Star") child.visible = (startType === "direct_star");
      if (child.name.startsWith("Link_Delta")) child.visible = (startType === "direct_delta");
    }
  });
  realModelRoot.scale.set(1.5, 1.5, 1.5);
  const box = new THREE.Box3().setFromObject(realModelRoot);
  realModelRoot.position.set(0, -box.min.y - 0.6, 0); 
  scene.add(realModelRoot);
}

const raycaster = new THREE.Raycaster(); const mouse = new THREE.Vector2(); const tooltip = document.getElementById("tooltip");

container.addEventListener('mousemove', (e) => {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1; mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
  tooltip.style.left = e.clientX + 15 + 'px'; tooltip.style.top = e.clientY + 15 + 'px';
  if(realModelRoot) {
      raycaster.setFromCamera(mouse, camera); const intersects = raycaster.intersectObject(realModelRoot, true);
      if (intersects.length > 0) {
        let curr = intersects[0].object; let pName = null;
        while(curr) { if(curr.userData && curr.userData.partName) { pName = curr.userData.partName; break; } curr = curr.parent; }
        if (pName) { tooltip.innerHTML = `<strong>${pName}</strong>`; tooltip.style.display = "block"; } else tooltip.style.display = "none";
      } else tooltip.style.display = "none";
  }
});

container.addEventListener('click', () => {
  if(!realModelRoot) return; initAudio(); raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObject(realModelRoot, true);
  if (intersects.length > 0) {
    let curr = intersects[0].object; let oName = null;
    while(curr) { if(curr.userData && curr.userData.partName) { oName = curr.name; break; } curr = curr.parent; }
    if (!oName) return;

    if (oName === "PanelDoor") { if(!checkProbesSafety()) return; doorOpen = !doorOpen; }
    else if (oName === "TerminalCover") {
        if(!checkProbesSafety()) return;
        if (lotoState !== 2 && !document.getElementById("bypass-mode").checked) triggerSecurityAlert("🛑 SÉCURITÉ : Consignez l'armoire (LOTO) pour ouvrir !");
        else { playSound('loto'); coverOpen = !coverOpen; const c = realModelRoot.getObjectByName("TerminalCover"); if(c) c.visible = !coverOpen; }
    }
    else if (oName === "SwitchHandle") {
      if(!checkProbesSafety()) return;
      if (lotoState === 0) {
        if(motorPhys.rpm > 50) triggerSecurityAlert("⚠️ SÉCURITÉ : Arrêtez le moteur avant de couper !");
        else { lotoState = 1; playSound('loto'); log("🔌 Sectionneur OFF."); }
      } 
      else if (lotoState === 1) { lotoState = 2; playSound('loto'); realModelRoot.getObjectByName("Padlock").visible = true; log("🔒 LOTO Actif."); }
      else { lotoState = 0; playSound('loto'); realModelRoot.getObjectByName("Padlock").visible = false; log("⚡ LOTO désactivé."); }
    }
    else if (oName.startsWith("Term_")) {
      const mode = document.getElementById("meter-mode").value;
      if (mode === "NONE") { triggerSecurityAlert("Allumez le multimètre d'abord."); return; }
      addProbe(oName.replace("Term_", ""));
    }
  }
});

function evaluateMeasurement() {
  if(probes.length < 2) return;
  const mode = document.getElementById("meter-mode").value; const disp = document.getElementById("meter-display");
  const p1 = probes[0], p2 = probes[1]; const isPowerOn = (lotoState === 0); const isRunning = (motorPhys.rpm > 50 && meterDisplayCurrent > 1);
  
  if (mode === "V_AC") {
    disp.style.color = "#ffaa00";
    if (isPowerOn && isRunning) {
      if (["U1","V1","W1","U2","V2","W2"].includes(p1) && p1!==p2) disp.innerText = (currentStartMode === "star_delta" && timeInRunPhase < timer_KT1) ? "230.0 V" : "400.0 V";
      else if (p1==="PE" || p2==="PE") disp.innerText = "230.0 V";
    } else disp.innerText = "0.0 V";
  } 
  else if (mode === "V_DC") {
    disp.style.color = "#ffaa00";
    if (isPowerOn && ((p1==="A1" && p2==="A2") || (p1==="A2" && p2==="A1"))) disp.innerText = isRunning ? "24.0 V" : "0.0 V"; else disp.innerText = "0.0 V";
  }
  else if (mode === "OHM") {
    disp.style.color = "#00ffff";
    if(isPowerOn) { disp.style.color="red"; disp.innerText = "ERR"; triggerSecurityAlert("💥 COURT-CIRCUIT ! Ohmmètre sous tension !"); }
    else {
      if ((p1==="95" && p2==="96") || (p1==="96" && p2==="95")) disp.innerText = (currentFault) ? "O.L (Ouvert)" : "0.1 Ω (Fermé)";
      else if (["U1","V1","W1","U2","V2","W2"].includes(p1) && ["U1","V1","W1","U2","V2","W2"].includes(p2)) disp.innerText = "2.5 Ω"; 
      else disp.innerText = "O.L";
    }
  }
  else if (mode === "MEG") { disp.style.color = "#ff00ff"; disp.innerText = "Prêt."; }
}

document.getElementById("btn-inject-meg").addEventListener("click", () => {
    if(probes.length < 2) return triggerSecurityAlert("Branchez 2 sondes pour le test d'isolement.");
    const isPowerOn = (lotoState === 0); const disp = document.getElementById("meter-display");
    if (isPowerOn) {
        disp.style.color="red"; disp.innerText = "EXPLOSION";
        triggerSmartFault("megger_destroyed", "💥 DESTRUCTION APPAREIL", "Vous avez injecté du DC dans un circuit sous tension. Le Mégohmmètre a explosé.\n\n🛠️ RÈGLE D'OR : La Consignation (LOTO) est OBLIGATOIRE avant un test d'isolement !");
        return;
    }
    playSound('megger'); const p1 = probes[0], p2 = probes[1];
    const isPhase = ["U1","V1","W1","U2","V2","W2"].includes(p1) || ["U1","V1","W1","U2","V2","W2"].includes(p2);
    const isPE = p1 === "PE" || p2 === "PE";
    
    setTimeout(() => {
        if (isPhase && isPE) {
            if (currentFault === "insulation_fault") { disp.innerText = "0.5 MΩ"; log("⚠️ Défaut d'isolement détecté (< 1 MΩ) !"); }
            else { disp.innerText = "> 500 MΩ"; log("✅ Isolement correct."); }
        } else if (isPhase && !isPE) { disp.innerText = "0.0 MΩ"; log("⚠️ Continuité (Enroulement)."); } 
        else { disp.innerText = "O.L"; }
    }, 500); 
});

// ==========================================
// BOUCLE PHYSIQUE ET OSCILLOSCOPE (60 FPS)
// ==========================================
let pulseClock = 0;
function animate() {
  requestAnimationFrame(animate); controls.update(); 
  let now = performance.now(); let dt = (now - lastTime) / 1000; if (dt > 0.1) dt = 0.1; lastTime = now;

  const isCommandedToRun = (currentSessionState.includes("run") || currentSessionState.includes("start")) && lotoState === 0 && !currentFault;
  timer_KT1 = parseFloat(document.getElementById("kt1-timer")?.value) || 4.0;

  let tau = 1.0; let I_steady = motorConfig.In; let RPM_steady = motorConfig.Nn;
  switch(motorConfig.loadType) {
     case 'no_load': tau = 0.2; I_steady = motorConfig.In * 0.35; RPM_steady = motorConfig.Ns * 0.995; break; 
     case 'pump_fan': tau = 1.2; I_steady = motorConfig.In * 0.90; RPM_steady = motorConfig.Nn; break; 
     case 'conveyor': tau = 3.0; I_steady = motorConfig.In * 1.0; RPM_steady = motorConfig.Nn; break; 
     case 'crusher': tau = 10.0; I_steady = motorConfig.In * 1.15; RPM_steady = motorConfig.Nn * 0.97; break; 
  }

  if (isCommandedToRun) {
      timeInRunPhase += dt; let targetRPMPhase = RPM_steady; let Id_multiplier = 6.0; 

      if (currentStartMode === "star_delta") {
          if (timeInRunPhase < timer_KT1) { 
              targetRPMPhase = RPM_steady * 0.80; 
              if (motorConfig.loadType === 'crusher' || motorConfig.loadType === 'conveyor') targetRPMPhase = RPM_steady * 0.15; 
              Id_multiplier = 2.0; 
          } else {
              if (timeInRunPhase > timer_KT1 && timeInRunPhase < timer_KT1 + 0.05) playSound('contactor_on'); 
              targetRPMPhase = RPM_steady;
              if (motorPhys.rpm < RPM_steady * 0.70) Id_multiplier = 5.0; 
              else Id_multiplier = 3.5; 
          }
      }

      motorPhys.rpm += (targetRPMPhase - motorPhys.rpm) * (dt / tau);
      if (motorPhys.rpm > targetRPMPhase) motorPhys.rpm = targetRPMPhase;

      let slip = 1.0 - (motorPhys.rpm / targetRPMPhase); if (slip < 0) slip = 0;
      let currentFactor = Math.pow(slip, 1.2); 
      motorPhys.current_true = I_steady + (motorConfig.In * Id_multiplier - I_steady) * currentFactor;

      if (slip <= 0.01) { motorPhys.current_true = I_steady + (Math.random() - 0.5) * 0.2; motorPhys.rpm = RPM_steady + (Math.random() - 0.5) * 1.5; }
  } else {
      timeInRunPhase = 0; motorPhys.current_true = 0;
      motorPhys.rpm += (0 - motorPhys.rpm) * (dt / (tau * 0.5)); 
      if (motorPhys.rpm < 2) motorPhys.rpm = 0;
  }

  meterDisplayCurrent += (motorPhys.current_true - meterDisplayCurrent) * (dt / 0.2);
  if (!isCommandedToRun && motorPhys.current_true === 0) meterDisplayCurrent = 0; 

  let heatGen = Math.pow(motorPhys.current_true / motorConfig.In, 2); 
  let tempDelta = (heatGen * 0.35 * dt) - ((motorPhys.temp - 20) * 0.05 * dt); 
  motorPhys.temp += tempDelta; if (motorPhys.temp < 20) motorPhys.temp = 20;
  if (motorPhys.temp >= 140 && !currentFault) triggerSmartFault("thermal_trip");

  // OSCILLOSCOPE
  oscDataI.push(motorPhys.current_true); oscDataN.push(motorPhys.rpm);
  if(oscDataI.length > 280) { oscDataI.shift(); oscDataN.shift(); }
  oscCtx.clearRect(0,0, oscCanvas.width, oscCanvas.height);
  
  oscCtx.beginPath(); oscCtx.strokeStyle = '#00ffff'; oscCtx.lineWidth = 2;
  for(let i=0; i<oscDataN.length; i++) {
      let x = (i/280)*oscCanvas.width; let y = oscCanvas.height - (oscDataN[i]/3000)*oscCanvas.height;
      if(i===0) oscCtx.moveTo(x,y); else oscCtx.lineTo(x,y);
  } oscCtx.stroke();
  
  oscCtx.beginPath(); oscCtx.strokeStyle = '#ffaa00'; oscCtx.lineWidth = 2;
  let maxI = motorConfig.In * 8;
  for(let i=0; i<oscDataI.length; i++) {
      let x = (i/280)*oscCanvas.width; let y = oscCanvas.height - (oscDataI[i]/maxI)*oscCanvas.height;
      if(i===0) oscCtx.moveTo(x,y); else oscCtx.lineTo(x,y);
  } oscCtx.stroke();

  document.getElementById("m-speed").textContent = Math.round(motorPhys.rpm);
  document.getElementById("m-current").textContent = meterDisplayCurrent.toFixed(1); 
  document.getElementById("m-temp").textContent = motorPhys.temp.toFixed(1);

  if (realModelRoot) {
    const rotor = realModelRoot.getObjectByName("RotorAssembly");
    if (rotor && motorPhys.rpm > 0) { rotationAngle += (motorPhys.rpm / motorConfig.Ns) * 0.3; rotor.rotation.x = rotationAngle; }
    const door = realModelRoot.getObjectByName("PanelDoor");
    if (door) door.rotation.y += ((doorOpen ? -Math.PI/1.6 : 0) - door.rotation.y) * 0.1;
    const handle = realModelRoot.getObjectByName("SwitchHandle");
    if (handle) handle.rotation.z += ((lotoState === 0 ? 0 : Math.PI/2) - handle.rotation.z) * 0.2;

    const ledRun = realModelRoot.getObjectByName("LED_Run"); const ledFault = realModelRoot.getObjectByName("LED_Fault"); const ledReset = realModelRoot.getObjectByName("LED_Reset"); 
    if (ledRun) { if (isCommandedToRun && motorPhys.rpm > 0) { ledRun.material.emissive.setHex(0x00ff00); ledRun.material.emissiveIntensity = 2; } else { ledRun.material.emissive.setHex(0x000000); } }
    if (ledFault) { if (currentFault) { ledFault.material.emissive.setHex(0xff0000); ledFault.material.emissiveIntensity = 2; } else { ledFault.material.emissive.setHex(0x000000); } }
    if (ledReset) { if (securityAlertTimer > 0) { securityAlertTimer--; pulseClock += 0.2; ledReset.material.emissive.setHex((Math.sin(pulseClock) > 0) ? 0xffff00 : 0x000000); ledReset.material.emissiveIntensity = 2; } else { ledReset.material.emissive.setHex(0x000000); } }
  }

  if (statorMaterial) {
    if (motorPhys.temp > 80 || currentFault) {
      pulseClock += 0.15; statorMaterial.emissive = new THREE.Color(0xff0000);
      let intensity = (motorPhys.temp - 80) / 100; if (intensity > 1) intensity = 1;
      statorMaterial.emissiveIntensity = ((Math.sin(pulseClock) + 1) / 2) * intensity;
    } else statorMaterial.emissiveIntensity = 0;
  }
  renderer.render(scene, camera);
}
animate();

// ==========================================
// EVENTS & UI
// ==========================================
function updateMeasurementsPanel(session) { currentSessionState = session.state; evaluateMeasurement(); }
function log(msg) { 
    console.log(msg); // Affichage console développeur aussi !
    const line = document.createElement("div"); line.textContent = `> ${msg}`; document.getElementById("log-panel")?.prepend(line); 
}

document.getElementById("btn-random-fault").addEventListener("click", () => {
  if (!currentSessionId || lotoState !== 0 || motorPhys.rpm === 0) return triggerSecurityAlert("Démarrez le moteur en charge d'abord !");
  api.injectFault(currentSessionId, "phase_loss").then(session => {
    currentFault = "phase_loss"; playSound('error'); updateMeasurementsPanel(session);
    document.getElementById("lm-title").innerText = "⚠️ DÉFAUT EXTÉRIEUR : Perte de Phase L1";
    document.getElementById("lm-symptom").innerText = "Le moteur grogne, perd de la vitesse, et le courant bondit.";
    document.getElementById("lm-hint").innerText = "Mesurez la tension sur le bornier du moteur.";
    document.getElementById("lm-lesson").innerText = "La rupture d'un câble a supprimé le champ tournant. Le courant bondit à I*sqrt(3) sur les phases saines. \n\n🛠️ ACTION : Arrêtez d'urgence, la surchauffe thermique est inévitable !";
    document.getElementById("lesson-modal").style.display = "block"; log(`⚠️ INJECTION DÉFAUT : Perte de Phase !`);
  });
});
document.getElementById("lm-close").addEventListener("click", () => document.getElementById("lesson-modal").style.display = "none");

async function generateMotor(isAuto) {
  const loading = document.getElementById("loading-screen");
  loading.style.display = "flex"; document.getElementById("loading-progress").style.width = "30%";
  try {
    updateMotorSpecs();
    const asset = await api.createAsset({ name: `Moteur`, electrical_properties: { rated_power_kw: motorConfig.P_kw, rated_voltage_v: 400, rated_current_a: motorConfig.In, frequency_hz: 50.0 }, mechanical_properties: { poles: motorConfig.poles, rated_speed_rpm: motorConfig.Nn, load_type: motorConfig.loadType }});
    currentAssetId = asset.id; document.getElementById("loading-txt").innerText = "Génération CAO 3D...";
    await api.generate3DModel(asset.id); document.getElementById("loading-progress").style.width = "80%";
    await loadRealMotorModel(asset.id); renderer.compile(scene, camera);
    
    currentStartMode = document.getElementById("start-type").value;
    const session = await api.createSession({ asset_id: asset.id });
    currentSessionId = session.id; currentFault = null; motorPhys = { rpm: 0, current_true: 0, temp: 20.0 }; meterDisplayCurrent = 0;
    updateMeasurementsPanel(session); startPolling();
    document.getElementById("loading-progress").style.width = "100%"; setTimeout(() => { loading.style.display = "none"; log("✅ Labo initialisé."); }, 500);
  } catch (e) { loading.innerHTML = `<h2 style='color:#ff4444;'>❌ Échec</h2><p>${e.message}</p><button id="btn-err" style="padding:10px; cursor:pointer;" onclick="document.getElementById('loading-screen').style.display='none'">Fermer</button>`; }
}

// 🌟 LOGIQUE DE CONNEXION FIABILISÉE
document.getElementById("btn-login").addEventListener("click", async () => {
  const btn = document.getElementById("btn-login");
  btn.innerText = "⏳ Connexion...";
  btn.disabled = true;
  try { 
    await api.registerAndLogin(document.getElementById("email").value, document.getElementById("password").value);
    document.getElementById("auth-status").textContent = `Connecté`; document.getElementById("auth-status").style.background = "#107c10";
    log("✅ Authentification réussie. Génération..."); 
    await generateMotor(true);
  } catch (e) { 
    log(`❌ Échec de connexion : ${e.message}`); 
    alert(`Échec de connexion au backend Python.\n\nVérifiez que le Port 8000 est bien sur "Public" dans GitHub Codespaces, et que l'URL dans index.html est la bonne.\n\nErreur détaillée : ${e.message}`);
  } finally {
    btn.innerText = "Connexion & Initialisation";
    btn.disabled = false;
  }
});
document.getElementById("btn-generate").addEventListener("click", () => generateMotor(false));

document.getElementById("btn-start").addEventListener("click", () => {
  initAudio();
  if (!currentSessionId) return;
  if (!checkProbesSafety()) return;
  if (coverOpen) return triggerSecurityAlert("❌ SÉCURITÉ : Refermez le capot bornier !");
  if (lotoState !== 0) return triggerSecurityAlert("❌ SÉCURITÉ : Armoire consignée.");
  if (currentFault) return triggerSecurityAlert("❌ DÉFAUT ACTIF : Réarmez l'installation (Reset) !");
  
  let f1_val = parseFloat(document.getElementById("dim-f1").value);
  if (f1_val < motorConfig.In * 0.95) {
      return triggerSmartFault("thermal_trip", "🛑 ERREUR DIMENSIONNEMENT", `Relais F1 réglé trop bas (${f1_val}A) pour le In du moteur (${motorConfig.In.toFixed(1)}A).\n\n🛠️ ACTION : Réglez F1 sur la valeur nominale du moteur.`);
  }

  timeInRunPhase = 0; currentStartMode = document.getElementById("start-type").value;
  oscDataI = []; oscDataN = []; 
  playSound('contactor_on');
  api.startSession(currentSessionId, (currentStartMode === "star_delta") ? "star_delta" : "direct").then(updateMeasurementsPanel);
});
document.getElementById("btn-stop").addEventListener("click", () => { initAudio(); if(currentSessionId) { playSound('contactor_off'); api.stopSession(currentSessionId).then(updateMeasurementsPanel); } });

document.getElementById("btn-reset-fault").addEventListener("click", async () => {
  initAudio(); if(!currentAssetId) return;
  if (!checkProbesSafety()) return;
  clearInterval(pollTimer); playSound('loto'); log("🔄 Purge du système et réarmement...");
  try {
      const newSession = await api.createSession({ asset_id: currentAssetId });
      currentSessionId = newSession.id; currentSessionState = "stopped"; currentFault = null; timeInRunPhase = 0;
      if(motorPhys.temp > 60) motorPhys.temp = 50.0; 
      log("✅ Réarmement réussi."); updateMeasurementsPanel(newSession);
  } catch(e) { log("❌ Erreur serveur."); } finally { startPolling(); }
});

function startPolling() { if (pollTimer) clearInterval(pollTimer); pollTimer = setInterval(async () => currentSessionId && api.tickSession(currentSessionId, 0.5).then(updateMeasurementsPanel), 500); }