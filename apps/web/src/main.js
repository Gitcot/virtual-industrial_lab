import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createApiClient } from "./apiClient.js";

const API_BASE_URL = window.VIL_API_BASE_URL; const api = createApiClient(API_BASE_URL);
let currentAssetId = null; let currentSessionId = null; let pollTimer = null;

// ==========================================
// DRAG & DROP SÉCURISÉ (Fix Fenêtres Disparues)
// ==========================================
function makeDraggable(panelId, headerId) {
    const panel = document.getElementById(panelId); 
    const header = document.getElementById(headerId);
    let isDragging = false, offsetX = 0, offsetY = 0;

    header.addEventListener('mousedown', (e) => {
        e.preventDefault();
        isDragging = true;
        const rect = panel.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        panel.style.position = 'fixed';
        panel.style.bottom = 'auto';
        panel.style.right = 'auto';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        e.preventDefault();
        
        let newLeft = e.clientX - offsetX;
        let newTop = e.clientY - offsetY;

        // Clamping : Empêche la fenêtre de déborder de l'écran
        const maxLeft = window.innerWidth - panel.offsetWidth;
        const maxTop = window.innerHeight - panel.offsetHeight;

        newLeft = Math.max(0, Math.min(maxLeft, newLeft));
        newTop = Math.max(0, Math.min(maxTop, newTop));

        panel.style.left = newLeft + 'px';
        panel.style.top = newTop + 'px';
    });

    document.addEventListener('mouseup', () => { isDragging = false; });
}

makeDraggable("oscilloscope-panel", "osc-header");
makeDraggable("fft-panel", "fft-header");
makeDraggable("schema-panel", "schema-header");

document.getElementById('start-type').addEventListener('change', (e) => {
    const v = e.target.value;
    document.getElementById('group-kt1').style.display = (v === 'star_delta') ? 'block' : 'none';
    document.getElementById('vfd-settings').style.display = (v === 'vfd' || v === 'soft_starter') ? 'block' : 'none';
    document.getElementById('group-freq').style.display = (v === 'vfd') ? 'block' : 'none';
});
document.getElementById('kt1-timer').addEventListener('input', (e) => document.getElementById('kt1-val').innerText = e.target.value + 's');
document.getElementById('meter-mode').addEventListener('change', (e) => {
    const val = e.target.value;
    document.getElementById('meg-options').style.display = (val === 'MEG') ? 'block' : 'none';
    document.getElementById('fft-panel').style.display = (val === 'VIB') ? 'flex' : 'none';
    document.getElementById('meter-display').innerText = (val === 'VIB') ? "FFT ACTIF" : "---";
});

// AUDIO
const AudioContext = window.AudioContext || window.webkitAudioContext; let audioCtx;
function initAudio() { if (!audioCtx) audioCtx = new AudioContext(); if (audioCtx.state === 'suspended') audioCtx.resume(); }
document.body.addEventListener('click', initAudio, { once: true });
function playSound(type) {
    if (!audioCtx) return; const t = audioCtx.currentTime; const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    if (type === 'contactor_on') { osc.type = 'square'; osc.frequency.setValueAtTime(100, t); osc.frequency.exponentialRampToValueAtTime(20, t + 0.1); gain.gain.setValueAtTime(0.8, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1); osc.start(t); osc.stop(t + 0.1); }
    else if (type === 'contactor_off') { osc.type = 'square'; osc.frequency.setValueAtTime(80, t); osc.frequency.exponentialRampToValueAtTime(10, t + 0.1); gain.gain.setValueAtTime(0.5, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1); osc.start(t); osc.stop(t + 0.1); }
    else if (type === 'error') { osc.type = 'sawtooth'; osc.frequency.setValueAtTime(150, t); osc.frequency.linearRampToValueAtTime(100, t + 0.3); gain.gain.setValueAtTime(0.3, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.3); osc.start(t); osc.stop(t + 0.3); }
    else if (type === 'megger') { osc.type = 'sine'; osc.frequency.setValueAtTime(2000, t); gain.gain.setValueAtTime(0.1, t); gain.gain.linearRampToValueAtTime(0.0, t + 0.5); osc.start(t); osc.stop(t + 0.5); }
}

// SCÈNE 3D
const container = document.getElementById("scene-container"); const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 0.1, 100); camera.position.set(2.5, 1.8, 3.2);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" }); renderer.setSize(window.innerWidth, window.innerHeight); renderer.shadowMap.enabled = true; container.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
scene.add(new THREE.AmbientLight(0xffffff, 0.7)); const dirLight = new THREE.DirectionalLight(0xffffff, 1.2); dirLight.position.set(3, 5, 4); dirLight.castShadow = true; scene.add(dirLight);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(15, 15), new THREE.MeshStandardMaterial({ color: 0x1a1c22 })); floor.rotation.x = -Math.PI / 2; floor.position.y = -0.6; floor.receiveShadow = true; scene.add(floor);
window.addEventListener('resize', () => { camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); });

// MODÈLE PHYSIQUE & VARIABLES
let realModelRoot = null; let statorMaterial = null;
let motorConfig = { P_kw: 11, poles: 4, Ns: 1500, Nn: 1450, In: 20.0, loadType: 'pump_fan' };
let motorPhys = { rpm: 0, current_true: 0, temp: 20.0 };
let meterDisplayCurrent = 0; let rotationAngle = 0;
let currentSessionState = "stopped"; let currentFault = null; 
let lotoState = 0; let doorOpen = false; let coverOpen = false; let probes = []; let securityAlertTimer = 0;
let currentStartMode = "direct_star"; let timeInRunPhase = 0; let lastTime = performance.now();
let timer_KT1 = 4.0; 

const oscCanvas = document.getElementById('osc-canvas'); const oscCtx = oscCanvas.getContext('2d'); let oscDataI = []; let oscDataN = [];
const fftCanvas = document.getElementById('fft-canvas'); const fftCtx = fftCanvas.getContext('2d');
const schemaCanvas = document.getElementById('schema-canvas'); const schemaCtx = schemaCanvas.getContext('2d');

function updateMotorSpecs() {
    motorConfig.P_kw = parseFloat(document.getElementById("np-power").value) || 11.0; motorConfig.poles = parseInt(document.getElementById("np-poles").value) || 4;
    motorConfig.loadType = document.getElementById("load-type").value; motorConfig.Ns = (120 * 50) / motorConfig.poles; motorConfig.Nn = motorConfig.Ns * 0.96; motorConfig.In = motorConfig.P_kw * 1.85; 
    document.getElementById("dim-f1").value = motorConfig.In.toFixed(1); document.getElementById("dim-q1").value = (motorConfig.In * 1.2).toFixed(1);
    if(parseFloat(document.getElementById("vfd-power").value) < motorConfig.P_kw) document.getElementById("vfd-power").value = (motorConfig.P_kw * 1.2).toFixed(1);
}

const DB_FAULTS = {
    "insulation": { type: "ELEC", title: "🛑 Défaut d'Isolement Stator", sym: "Le disjoncteur différentiel saute.", hint: "Mégohmmètre entre U1 et Terre.", lesson: "Vernis fondu (court-circuit à la carcasse). Testez au Mégohmmètre (Valeur < 1 MΩ)." },
    "phase_loss": { type: "ELEC", title: "⚠️ Perte de Phase L1", sym: "Le moteur grogne et chauffe énormément.", hint: "Vérifiez la tension (V AC) sur le bornier U1-V1-W1.", lesson: "Un câble réseau est rompu. Le moteur tourne sur 2 phases et tire I*sqrt(3)." },
    "undervoltage": { type: "ELEC", title: "⚠️ Chute de Tension Réseau", sym: "Vitesse faible, courant élevé en régime nominal.", hint: "Lisez la tension V AC en marche.", lesson: "Réseau à 340V au lieu de 400V. Le moteur tire plus de courant pour fournir la même puissance mécanique." },
    "mech_unbalance": { type: "MECH", title: "⚙️ Balourd (Unbalance)", sym: "Fortes vibrations à basse fréquence.", hint: "Utilisez l'analyseur FFT.", lesson: "Hélice ébréchée ou dépôt de matière. Le spectre FFT montre un pic d'amplitude géant à 1X RPM." },
    "mech_misalign": { type: "MECH", title: "⚙️ Défaut d'Alignement", sym: "Bruit cyclique sur l'accouplement.", hint: "Utilisez l'analyseur FFT.", lesson: "Arbre moteur et charge désaxés. Le spectre FFT montre des pics sur 1X et 2X RPM." },
    "mech_bearing": { type: "MECH", title: "⚙️ Écaillage Roulement", sym: "Sifflement aigu constant.", hint: "Utilisez l'analyseur FFT.", lesson: "Billes ou pistes endommagées. Le spectre FFT montre un nuage de pics à haute fréquence (100-150 Hz)." }
};

function triggerSmartFault(id, customTitle=null, customLesson=null) {
    if(currentFault) return; playSound('error'); currentFault = id;
    let title = customTitle, symptom = "Mise en sécurité.", hint = "Vérifiez les paramètres.", lesson = customLesson;
    if (DB_FAULTS[id]) { title = DB_FAULTS[id].title; symptom = DB_FAULTS[id].sym; hint = DB_FAULTS[id].hint; lesson = DB_FAULTS[id].lesson; } 
    else if (id === "thermal_trip" && !customTitle) {
        title = "🛑 DÉCLENCHEMENT THERMIQUE (F1)"; symptom = "Arrêt net. Courbe I²t dépassée.";
        if (currentStartMode === "star_delta" && timer_KT1 < 4.0) { hint = "Tempo KT1 trop courte."; lesson = "Passage Triangle prématuré = Pic de courant colossal."; } 
        else { hint = "Surcharge ou inertie trop forte."; lesson = "Le moteur tire trop de courant trop longtemps."; }
    } else if (id === "soft_trip") {
        title = "🛑 DÉFAUT SOFT-STARTER"; symptom = "Le démarreur a coupé avant la fin du démarrage."; hint = "Regardez la vitesse atteinte.";
        lesson = "La tension réduite du Soft-Starter ne fournit pas assez de couple pour vaincre l'inertie de cette charge lourde (Rotor quasi-bloqué). Le démarreur s'est mis en sécurité thermique interne (Start Time Exceeded).\n\n🛠️ ACTION : Utilisez un Variateur (VFD) ou démarrez en Direct.";
    }
    document.getElementById("lm-title").innerText = title; document.getElementById("lm-symptom").innerText = symptom;
    document.getElementById("lm-hint").innerText = hint; document.getElementById("lm-lesson").innerText = lesson;
    document.getElementById("lesson-modal").style.display = "block"; log(`💥 Pannes/Diagnostic : ${title}`);
}

function triggerSecurityAlert(msg) { playSound('error'); log(msg); securityAlertTimer = 180; }
function addProbe(tName) { if (probes.length >= 2) probes.shift(); if (!probes.includes(tName)) probes.push(tName); document.getElementById("probe-status").innerText = `Sondes : [ ${probes.join(" | ")} ]`; evaluateMeasurement(); }
document.getElementById("btn-clear-probes").addEventListener("click", () => { probes = []; document.getElementById("probe-status").innerText = `Sondes : (Aucune)`; document.getElementById("meter-display").innerText = "0.00"; });
function checkProbesSafety() { if (probes.length > 0) { triggerSecurityAlert("❌ SÉCURITÉ : Retirez les sondes avant de manipuler l'installation !"); return false; } return true; }

// ==========================================
// 🌟 FOLIO ÉLECTRIQUE INTELLIGENT ET DYNAMIQUE
// ==========================================
function drawSchematic() {
    if(document.getElementById('schema-panel').style.display === 'none') return;
    
    schemaCtx.clearRect(0,0, schemaCanvas.width, schemaCanvas.height);
    const isPowerOn = (lotoState === 0);
    const isRunning = (currentSessionState.includes("run") || currentSessionState.includes("start")) && isPowerOn && !currentFault;
    const isFault = (currentFault === "thermal_trip");

    // Couleurs
    const cPower = isPowerOn ? "#ff4444" : "#555"; 
    const cRun = isRunning ? "#ff4444" : "#555";
    const cCmd = isPowerOn ? "#ff00ff" : "#555"; 
    const cGND = "#00ffff"; 
    
    schemaCtx.lineWidth = 2; schemaCtx.font = "10px Arial";

    // --- MODE 1 : DÉMARRAGE DIRECT (DOL) ---
    if (currentStartMode === "direct_star" || currentStartMode === "direct_delta") {
        // PUISSANCE
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("PUISSANCE (DOL 400V)", 10, 20);
        schemaCtx.strokeStyle = cPower;
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(20 + i*15, 30); schemaCtx.lineTo(20 + i*15, 50); schemaCtx.stroke(); }
        
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("Q1", 70, 60);
        for(let i=0; i<3; i++) { 
            schemaCtx.beginPath(); schemaCtx.moveTo(20 + i*15, 50); schemaCtx.lineTo(20 + i*15 + (isPowerOn ? 0 : 6), 70); schemaCtx.stroke(); 
            schemaCtx.beginPath(); schemaCtx.moveTo(20 + i*15, 70); schemaCtx.lineTo(20 + i*15, 90); schemaCtx.strokeStyle = isPowerOn ? cPower : "#555"; schemaCtx.stroke();
        }

        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("KM1", 70, 100);
        for(let i=0; i<3; i++) { 
            schemaCtx.beginPath(); schemaCtx.moveTo(20 + i*15, 90); schemaCtx.lineTo(20 + i*15 + (isRunning ? 0 : 6), 110); schemaCtx.stroke(); 
            schemaCtx.beginPath(); schemaCtx.moveTo(20 + i*15, 110); schemaCtx.lineTo(20 + i*15, 130); schemaCtx.strokeStyle = isRunning ? cPower : "#555"; schemaCtx.stroke();
        }

        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("F1", 70, 140);
        for(let i=0; i<3; i++) { 
            schemaCtx.beginPath(); schemaCtx.rect(15 + i*15, 130, 10, 20); schemaCtx.stroke(); 
            schemaCtx.beginPath(); schemaCtx.moveTo(20 + i*15, 150); schemaCtx.lineTo(20 + i*15, 180); schemaCtx.stroke();
        }
        schemaCtx.beginPath(); schemaCtx.arc(35, 200, 20, 0, 2*Math.PI); schemaCtx.stroke();
        schemaCtx.fillStyle = isRunning ? "#0f0" : "#fff"; schemaCtx.fillText("M3~", 25, 205);

        // COMMANDE
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("COMMANDE (24V DC)", 160, 20);
        schemaCtx.strokeStyle = cCmd; schemaCtx.beginPath(); schemaCtx.moveTo(160, 30); schemaCtx.lineTo(320, 30); schemaCtx.stroke(); schemaCtx.fillText("+24V", 330, 33);
        
        // F1 (95-96 NF)
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 30); schemaCtx.lineTo(200, 50); schemaCtx.stroke();
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("F1 95-96", 215, 60);
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 50); schemaCtx.lineTo(200 + (isFault ? 8 : 0), 70); schemaCtx.stroke();
        
        let cmdLive = isPowerOn && !isFault;
        schemaCtx.strokeStyle = cmdLive ? cCmd : "#555";
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 70); schemaCtx.lineTo(200, 90); schemaCtx.stroke();

        // S0 (Arrêt NF)
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("S0 (Stop)", 215, 100);
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 90); schemaCtx.lineTo(200, 110); schemaCtx.stroke();
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 110); schemaCtx.lineTo(200, 130); schemaCtx.stroke();

        // Branchement S1 / Auto-maintien KM1 13-14 (🌟 RIGOUREUSEMENT OUVERT À L'ARRÊT !)
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("S1 (Marche)", 235, 140);
        schemaCtx.fillText("KM1 13-14", 125, 140);
        
        // S1 (Marche NO)
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 130); schemaCtx.lineTo(200 + 6, 150); schemaCtx.stroke();
        
        // Auto-maintien KM1 (NO) - Ouvert à l'arrêt !
        schemaCtx.beginPath(); 
        schemaCtx.moveTo(200, 120); schemaCtx.lineTo(170, 120); schemaCtx.lineTo(170, 130);
        schemaCtx.lineTo(170 + (isRunning ? 0 : 6), 150); // Gap de 6px si arreté !
        schemaCtx.lineTo(170, 160); schemaCtx.lineTo(200, 160); 
        schemaCtx.stroke();

        // Fil vers bobine KM1
        let coilLive = cmdLive && isRunning;
        schemaCtx.strokeStyle = coilLive ? cCmd : "#555";
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 150); schemaCtx.lineTo(200, 180); schemaCtx.stroke();
        
        // Bobine KM1 A1-A2
        schemaCtx.beginPath(); schemaCtx.rect(190, 180, 20, 30); 
        schemaCtx.fillStyle = coilLive ? "#ff00ff" : "transparent"; schemaCtx.fill(); schemaCtx.stroke();
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("KM1", 215, 200);

        // Ligne 0V
        schemaCtx.strokeStyle = cGND;
        schemaCtx.beginPath(); schemaCtx.moveTo(200, 210); schemaCtx.lineTo(200, 230); schemaCtx.lineTo(320, 230); schemaCtx.stroke();
        schemaCtx.fillText("0V", 330, 233);
    } 
    // --- MODE 2 : ÉTOILE-TRIANGLE (Y/Δ) ---
    else if (currentStartMode === "star_delta") {
        let isStarPhase = isRunning && timeInRunPhase < timer_KT1;
        let isDeltaPhase = isRunning && timeInRunPhase >= timer_KT1;

        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("PUISSANCE (Étoile-Triangle)", 10, 20);
        schemaCtx.strokeStyle = cPower;
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(15+i*10, 30); schemaCtx.lineTo(15+i*10, 50); schemaCtx.stroke(); }
        
        // Q1
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(15+i*10, 50); schemaCtx.lineTo(15+i*10+(isPowerOn?0:5), 65); schemaCtx.stroke(); schemaCtx.beginPath(); schemaCtx.moveTo(15+i*10, 65); schemaCtx.lineTo(15+i*10, 80); schemaCtx.stroke(); }
        
        // KM1 (Ligne)
        schemaCtx.fillText("KM1", 50, 90);
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(15+i*10, 80); schemaCtx.lineTo(15+i*10+(isRunning?0:5), 95); schemaCtx.stroke(); schemaCtx.beginPath(); schemaCtx.moveTo(15+i*10, 95); schemaCtx.lineTo(15+i*10, 110); schemaCtx.stroke(); }

        // KM2 (Triangle) & KM3 (Étoile)
        schemaCtx.fillText("KM2(Δ)", 65, 125); schemaCtx.fillText("KM3(Y)", 115, 125);
        for(let i=0; i<3; i++) {
            // KM2
            schemaCtx.strokeStyle = isDeltaPhase ? cPower : "#555";
            schemaCtx.beginPath(); schemaCtx.moveTo(60+i*10, 110); schemaCtx.lineTo(60+i*10+(isDeltaPhase?0:5), 125); schemaCtx.stroke();
            // KM3
            schemaCtx.strokeStyle = isStarPhase ? cPower : "#555";
            schemaCtx.beginPath(); schemaCtx.moveTo(110+i*10, 110); schemaCtx.lineTo(110+i*10+(isStarPhase?0:5), 125); schemaCtx.stroke();
        }

        // Moteur M3~
        schemaCtx.beginPath(); schemaCtx.arc(30, 150, 15, 0, 2*Math.PI); schemaCtx.strokeStyle = isRunning ? cPower : "#555"; schemaCtx.stroke();
        schemaCtx.fillStyle = isRunning ? "#0f0" : "#fff"; schemaCtx.fillText("M3~", 22, 153);

        // Commande Y/Δ
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("COMMANDE AUTOMATISÉE", 180, 20);
        schemaCtx.strokeStyle = isPowerOn ? cCmd : "#555"; schemaCtx.beginPath(); schemaCtx.moveTo(180, 30); schemaCtx.lineTo(380, 30); schemaCtx.stroke();
        
        // Bobines KM1, KT1, KM3, KM2
        schemaCtx.fillStyle = isRunning ? "#ff00ff" : "#555";
        schemaCtx.fillText("KM1(Ligne)", 190, 180);
        schemaCtx.fillText("KT1(Tempo)", 240, 180);
        schemaCtx.fillStyle = isStarPhase ? "#ff00ff" : "#555"; schemaCtx.fillText("KM3(Y)", 295, 180);
        schemaCtx.fillStyle = isDeltaPhase ? "#ff00ff" : "#555"; schemaCtx.fillText("KM2(Δ)", 340, 180);
        
        for(let x of [200, 250, 300, 350]) {
            schemaCtx.beginPath(); schemaCtx.rect(x-10, 190, 20, 25); schemaCtx.strokeStyle = "#fff"; schemaCtx.stroke();
            schemaCtx.beginPath(); schemaCtx.moveTo(x, 215); schemaCtx.lineTo(x, 230); schemaCtx.strokeStyle = cGND; schemaCtx.stroke();
        }
        schemaCtx.beginPath(); schemaCtx.moveTo(180, 230); schemaCtx.lineTo(380, 230); schemaCtx.stroke();
    }
    // --- MODE 3 : VARIATEUR (VFD) OU SOFT-STARTER ---
    else {
        let isVFD = (currentStartMode === "vfd");
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText(isVFD ? "PUISSANCE (VFD / PWM)" : "PUISSANCE (SOFT-STARTER)", 10, 20);
        schemaCtx.strokeStyle = cPower;
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(20+i*15, 30); schemaCtx.lineTo(20+i*15, 60); schemaCtx.stroke(); }
        
        // Q1
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(20+i*15, 60); schemaCtx.lineTo(20+i*15+(isPowerOn?0:5), 80); schemaCtx.stroke(); schemaCtx.beginPath(); schemaCtx.moveTo(20+i*15, 80); schemaCtx.lineTo(20+i*15, 100); schemaCtx.stroke(); }

        // BLOC VFD / SOFT
        schemaCtx.beginPath(); schemaCtx.rect(10, 100, 70, 60); schemaCtx.fillStyle = "rgba(0,255,255,0.1)"; schemaCtx.fill(); schemaCtx.strokeStyle = "#00ffff"; schemaCtx.stroke();
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText(isVFD ? "VFD (=/~)" : "SOFT (⧻)", 15, 135);

        // Sortie Moteur
        for(let i=0; i<3; i++) { schemaCtx.beginPath(); schemaCtx.moveTo(20+i*15, 160); schemaCtx.lineTo(20+i*15, 180); schemaCtx.strokeStyle = isRunning ? cPower : "#555"; schemaCtx.stroke(); }
        schemaCtx.beginPath(); schemaCtx.arc(35, 200, 18, 0, 2*Math.PI); schemaCtx.stroke();
        schemaCtx.fillStyle = isRunning ? "#0f0" : "#fff"; schemaCtx.fillText("M3~", 25, 205);

        // Bornier de commande VFD
        schemaCtx.fillStyle = "#fff"; schemaCtx.fillText("BORNES CONTRÔLE VFD", 160, 20);
        schemaCtx.strokeStyle = isPowerOn ? cCmd : "#555";
        schemaCtx.beginPath(); schemaCtx.moveTo(180, 40); schemaCtx.lineTo(280, 40); schemaCtx.stroke(); schemaCtx.fillText("+24V Out", 290, 43);
        schemaCtx.beginPath(); schemaCtx.moveTo(180, 80); schemaCtx.lineTo(180+(isRunning?0:6), 100); schemaCtx.stroke(); schemaCtx.fillText("LI1 (FWD)", 200, 90);
        schemaCtx.beginPath(); schemaCtx.moveTo(180, 100); schemaCtx.lineTo(280, 100); schemaCtx.stroke();
    }
}

// SCÈNE 3D CHARGEMENT ET INTERACTION
const raycaster = new THREE.Raycaster(); 
const mouse = new THREE.Vector2(); 
const tooltip = document.getElementById("tooltip");

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
      if (child.name === "Link_Star") child.visible = (startType === "direct_star" || startType === "soft_starter" || startType === "vfd");
      if (child.name.startsWith("Link_Delta")) child.visible = (startType === "direct_delta");
    }
  });
  realModelRoot.scale.set(1.5, 1.5, 1.5); const box = new THREE.Box3().setFromObject(realModelRoot); realModelRoot.position.set(0, -box.min.y - 0.6, 0); scene.add(realModelRoot);
}

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
        if (lotoState !== 2 && !document.getElementById("bypass-mode").checked) triggerSecurityAlert("🛑 SÉCURITÉ : Consignez (LOTO) pour ouvrir !");
        else { playSound('loto'); coverOpen = !coverOpen; const c = realModelRoot.getObjectByName("TerminalCover"); if(c) c.visible = !coverOpen; }
    }
    else if (oName === "SwitchHandle") {
      if(!checkProbesSafety()) return;
      if (lotoState === 0) { if(motorPhys.rpm > 50) triggerSecurityAlert("⚠️ SÉCURITÉ : Arrêtez avant de couper !"); else { lotoState = 1; playSound('loto'); log("🔌 OFF."); } } 
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
  let v_reseau = (currentFault === "undervoltage") ? 340.0 : 400.0;
  
  if (mode === "V_AC") { disp.style.color = "#ffaa00"; if (isPowerOn && isRunning) { if (["U1","V1","W1","U2","V2","W2"].includes(p1) && p1!==p2) disp.innerText = (currentStartMode === "star_delta" && timeInRunPhase < timer_KT1) ? (v_reseau/1.73).toFixed(1)+" V" : v_reseau.toFixed(1)+" V"; else if (p1==="PE" || p2==="PE") disp.innerText = "230.0 V"; } else disp.innerText = "0.0 V"; } 
  else if (mode === "V_DC") { disp.style.color = "#ffaa00"; disp.innerText = (isPowerOn && isRunning && ((p1==="A1" && p2==="A2") || (p1==="A2" && p2==="A1"))) ? "24.0 V" : "0.0 V"; }
  else if (mode === "OHM") { disp.style.color = "#00ffff"; if(isPowerOn) { disp.style.color="red"; disp.innerText = "ERR"; triggerSecurityAlert("💥 COURT-CIRCUIT ! Ohmmètre sous tension !"); } else { if ((p1==="95" && p2==="96") || (p1==="96" && p2==="95")) disp.innerText = (currentFault === "thermal_trip") ? "O.L (Ouvert)" : "0.1 Ω (Fermé)"; else if (["U1","V1","W1","U2","V2","W2"].includes(p1) && ["U1","V1","W1","U2","V2","W2"].includes(p2)) disp.innerText = "2.5 Ω"; else disp.innerText = "O.L"; } }
}

document.getElementById("btn-inject-meg").addEventListener("click", () => {
    if(probes.length < 2) return triggerSecurityAlert("Branchez 2 sondes pour l'isolement.");
    if (lotoState === 0) { triggerSmartFault("megger_destroyed", "💥 DESTRUCTION APPAREIL", "Injection DC dans un circuit sous tension. LOTO OBLIGATOIRE !"); return; }
    playSound('megger'); const p1 = probes[0], p2 = probes[1];
    const isPhase = ["U1","V1","W1","U2","V2","W2"].includes(p1) || ["U1","V1","W1","U2","V2","W2"].includes(p2); const isPE = p1 === "PE" || p2 === "PE";
    setTimeout(() => { const disp = document.getElementById("meter-display");
        if (isPhase && isPE) { if (currentFault === "insulation") { disp.innerText = "0.5 MΩ"; log("⚠️ Défaut isolement (< 1 MΩ) !"); } else { disp.innerText = "> 500 MΩ"; log("✅ Isolement correct."); } } 
        else if (isPhase && !isPE) { disp.innerText = "0.0 MΩ"; log("⚠️ Continuité (Enroulement)."); } else { disp.innerText = "O.L"; }
    }, 500); 
});

// BOUCLE ANIMATION (60 FPS)
function animate() {
  requestAnimationFrame(animate); controls.update(); 
  let now = performance.now(); let dt = (now - lastTime) / 1000; if (dt > 0.1) dt = 0.1; lastTime = now;

  const isCommandedToRun = (currentSessionState.includes("run") || currentSessionState.includes("start")) && lotoState === 0 && !currentFault;
  timer_KT1 = parseFloat(document.getElementById("kt1-timer")?.value) || 4.0;
  let v_ramp = parseFloat(document.getElementById("vfd-ramp")?.value) || 5.0;
  let v_freq = parseFloat(document.getElementById("vfd-freq")?.value) || 50.0;
  let v_pwr = parseFloat(document.getElementById("vfd-power")?.value) || 15.0;

  let tau = 1.0; let I_steady = motorConfig.In; let RPM_steady = motorConfig.Nn;
  switch(motorConfig.loadType) { case 'no_load': tau = 0.2; I_steady = motorConfig.In * 0.35; break; case 'pump_fan': tau = 1.2; I_steady = motorConfig.In * 0.90; break; case 'conveyor': tau = 3.0; I_steady = motorConfig.In * 1.0; break; case 'crusher': tau = 10.0; I_steady = motorConfig.In * 1.15; break; }
  if (currentFault === "undervoltage") { RPM_steady *= 0.90; I_steady *= 1.15; } 

  if (isCommandedToRun) {
      timeInRunPhase += dt; let targetRPMPhase = RPM_steady; let Id_multiplier = 6.0; 
      if (currentStartMode === "star_delta") {
          if (timeInRunPhase < timer_KT1) { targetRPMPhase = RPM_steady * 0.80; if (motorConfig.loadType === 'crusher' || motorConfig.loadType === 'conveyor') targetRPMPhase = RPM_steady * 0.15; Id_multiplier = 2.0; } 
          else { if (timeInRunPhase > timer_KT1 && timeInRunPhase < timer_KT1 + 0.05) playSound('contactor_on'); targetRPMPhase = RPM_steady; Id_multiplier = (motorPhys.rpm < RPM_steady * 0.70) ? 5.0 : 3.5; }
      } 
      else if (currentStartMode === "soft_starter") {
          if (timeInRunPhase < v_ramp) { Id_multiplier = 3.0; targetRPMPhase = RPM_steady * 0.9; if (motorConfig.loadType === 'crusher') targetRPMPhase = RPM_steady * 0.15; } 
          else { if (motorPhys.rpm < RPM_steady * 0.8) { triggerSmartFault("soft_trip"); } else { targetRPMPhase = RPM_steady; Id_multiplier = 3.5; } }
      }
      else if (currentStartMode === "vfd") {
          if (v_pwr < motorConfig.P_kw) triggerSmartFault("vfd_ocf", "🛑 DÉFAUT VFD (OCF)", "Variateur sous-dimensionné. Surintensité interne.");
          let current_hz = (timeInRunPhase < v_ramp) ? (timeInRunPhase / v_ramp) * v_freq : v_freq;
          targetRPMPhase = ((120 * current_hz) / motorConfig.poles) * 0.96; Id_multiplier = 1.2; motorPhys.rpm = targetRPMPhase; 
      }

      if(currentStartMode !== "vfd") { motorPhys.rpm += (targetRPMPhase - motorPhys.rpm) * (dt / tau); if (motorPhys.rpm > targetRPMPhase) motorPhys.rpm = targetRPMPhase; }

      if(currentStartMode !== "vfd") {
          let slip = 1.0 - (motorPhys.rpm / RPM_steady); if (slip < 0) slip = 0;
          let currentFactor = Math.pow(slip, 1.2); motorPhys.current_true = I_steady + (motorConfig.In * Id_multiplier - I_steady) * currentFactor;
          if (slip <= 0.01) { motorPhys.current_true = I_steady + (Math.random()-0.5)*0.2; motorPhys.rpm = RPM_steady + (Math.random()-0.5)*1.5; }
      } else {
          let loadRatio = motorPhys.rpm / motorConfig.Nn; motorPhys.current_true = (I_steady * loadRatio) + (motorConfig.In * 0.3) + (Math.random()-0.5)*0.1;
      }
      if (currentFault === "phase_loss") { motorPhys.current_true = I_steady * 1.73; motorPhys.rpm = RPM_steady * 0.90; }

  } else {
      timeInRunPhase = 0; motorPhys.current_true = 0; motorPhys.rpm += (0 - motorPhys.rpm) * (dt / (tau * 0.5)); if (motorPhys.rpm < 2) motorPhys.rpm = 0;
  }

  meterDisplayCurrent += (motorPhys.current_true - meterDisplayCurrent) * (dt / 0.2);
  if (!isCommandedToRun && motorPhys.current_true === 0) meterDisplayCurrent = 0; 

  let heatGen = Math.pow(motorPhys.current_true / motorConfig.In, 2); 
  let tempDelta = (heatGen * 0.35 * dt) - ((motorPhys.temp - 20) * 0.05 * dt); 
  motorPhys.temp += tempDelta; if (motorPhys.temp < 20) motorPhys.temp = 20;
  if (motorPhys.temp >= 140 && !currentFault) triggerSmartFault("thermal_trip");

  if(document.getElementById('oscilloscope-panel').style.display !== 'none') {
      oscDataI.push(motorPhys.current_true); oscDataN.push(motorPhys.rpm);
      if(oscDataI.length > 280) { oscDataI.shift(); oscDataN.shift(); }
      oscCtx.clearRect(0,0, oscCanvas.width, oscCanvas.height);
      oscCtx.beginPath(); oscCtx.strokeStyle = '#00ffff'; oscCtx.lineWidth = 2;
      for(let i=0; i<oscDataN.length; i++) { let x=(i/280)*oscCanvas.width; let y=oscCanvas.height-(oscDataN[i]/3000)*oscCanvas.height; if(i===0) oscCtx.moveTo(x,y); else oscCtx.lineTo(x,y); } oscCtx.stroke();
      oscCtx.beginPath(); oscCtx.strokeStyle = '#ffaa00'; oscCtx.lineWidth = 2;
      let maxI = motorConfig.In * 8;
      for(let i=0; i<oscDataI.length; i++) { let x=(i/280)*oscCanvas.width; let y=oscCanvas.height-(oscDataI[i]/maxI)*oscCanvas.height; if(i===0) oscCtx.moveTo(x,y); else oscCtx.lineTo(x,y); } oscCtx.stroke();
  }

  if (document.getElementById('meter-mode').value === 'VIB') {
      fftCtx.clearRect(0,0, fftCanvas.width, fftCanvas.height); fftCtx.strokeStyle = '#444'; fftCtx.lineWidth = 1;
      for(let i=0; i<5; i++) { let x = (i/5)*fftCanvas.width; fftCtx.beginPath(); fftCtx.moveTo(x,0); fftCtx.lineTo(x,fftCanvas.height); fftCtx.stroke(); }
      fftCtx.beginPath(); fftCtx.strokeStyle = '#0f0'; fftCtx.lineWidth = 2;
      let f_rot = motorPhys.rpm / 60; 
      for(let x=0; x<fftCanvas.width; x++) {
          let hz = (x / fftCanvas.width) * 200; let amplitude = 1.0 + Math.random()*0.5; 
          if (f_rot > 5) {
              if (Math.abs(hz - f_rot) < 2) amplitude += 5.0; 
              if (currentFault === "mech_unbalance" && Math.abs(hz - f_rot) < 3) amplitude += 40.0; 
              if (currentFault === "mech_misalign") { if (Math.abs(hz - f_rot) < 3) amplitude += 20.0; if (Math.abs(hz - f_rot*2) < 3) amplitude += 30.0; }
              if (currentFault === "mech_bearing" && hz > 100 && hz < 150) { if(Math.random() > 0.8) amplitude += 25.0; }
          }
          let y = fftCanvas.height - Math.min(amplitude, fftCanvas.height);
          if(x===0) fftCtx.moveTo(x,y); else fftCtx.lineTo(x,y);
      } fftCtx.stroke();
  }

  drawSchematic();

  const elSpeed = document.getElementById("m-speed"); if(elSpeed) elSpeed.textContent = Math.round(motorPhys.rpm);
  const elCurrent = document.getElementById("m-current"); if(elCurrent) elCurrent.textContent = meterDisplayCurrent.toFixed(1); 
  const elTemp = document.getElementById("m-temp"); if(elTemp) elTemp.textContent = motorPhys.temp.toFixed(1);
  evaluateMeasurement();

  if (realModelRoot) {
    const rotor = realModelRoot.getObjectByName("RotorAssembly");
    if (rotor && motorPhys.rpm > 0) { rotationAngle += (motorPhys.rpm / motorConfig.Ns) * 0.3; rotor.rotation.x = rotationAngle; }
    const door = realModelRoot.getObjectByName("PanelDoor"); if (door) door.rotation.y += ((doorOpen ? -Math.PI/1.6 : 0) - door.rotation.y) * 0.1;
    const handle = realModelRoot.getObjectByName("SwitchHandle"); if (handle) handle.rotation.z += ((lotoState === 0 ? 0 : Math.PI/2) - handle.rotation.z) * 0.2;
    const ledRun = realModelRoot.getObjectByName("LED_Run"); const ledFault = realModelRoot.getObjectByName("LED_Fault"); const ledReset = realModelRoot.getObjectByName("LED_Reset"); 
    if (ledRun) { if (isCommandedToRun && motorPhys.rpm > 0) { ledRun.material.emissive.setHex(0x00ff00); ledRun.material.emissiveIntensity = 2; } else { ledRun.material.emissive.setHex(0x000000); } }
    if (ledFault) { if (currentFault) { ledFault.material.emissive.setHex(0xff0000); ledFault.material.emissiveIntensity = 2; } else { ledFault.material.emissive.setHex(0x000000); } }
    if (ledReset) { if (securityAlertTimer > 0) { securityAlertTimer--; pulseClock += 0.2; ledReset.material.emissive.setHex((Math.sin(pulseClock) > 0) ? 0xffff00 : 0x000000); ledReset.material.emissiveIntensity = 2; } else { ledReset.material.emissive.setHex(0x000000); } }
  }
  if (statorMaterial) {
    if (motorPhys.temp > 80 || currentFault) { pulseClock += 0.15; statorMaterial.emissive = new THREE.Color(0xff0000); let intensity = (motorPhys.temp - 80) / 100; if (intensity > 1) intensity = 1; statorMaterial.emissiveIntensity = ((Math.sin(pulseClock) + 1) / 2) * intensity;
    } else statorMaterial.emissiveIntensity = 0;
  }
  renderer.render(scene, camera);
}
animate();

// EVENTS & UI
function updateMeasurementsPanel(session) { currentSessionState = session.state; evaluateMeasurement(); }
function log(msg) { console.log(msg); const line = document.createElement("div"); line.textContent = `> ${msg}`; document.getElementById("log-panel")?.prepend(line); }

document.getElementById("btn-rand-elec").addEventListener("click", () => {
    if (!currentSessionId || lotoState !== 0) return triggerSecurityAlert("Le TGBT doit être alimenté !");
    const faults = ["insulation", "phase_loss", "undervoltage"]; triggerSmartFault(faults[Math.floor(Math.random() * faults.length)]);
});
document.getElementById("btn-rand-mech").addEventListener("click", () => {
    if (!currentSessionId || motorPhys.rpm < 100) return triggerSecurityAlert("Le moteur doit tourner !");
    const faults = ["mech_unbalance", "mech_misalign", "mech_bearing"]; triggerSmartFault(faults[Math.floor(Math.random() * faults.length)]);
});
document.getElementById("lm-close").addEventListener("click", () => document.getElementById("lesson-modal").style.display = "none");

async function generateMotor(isAuto) {
  const loading = document.getElementById("loading-screen"); loading.style.display = "flex"; document.getElementById("loading-progress").style.width = "30%";
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

document.getElementById("btn-login").addEventListener("click", async () => {
  const btn = document.getElementById("btn-login"); btn.innerText = "⏳ Connexion..."; btn.disabled = true;
  try { 
    await api.registerAndLogin(document.getElementById("email").value, document.getElementById("password").value);
    document.getElementById("auth-status").textContent = `Connecté`; document.getElementById("auth-status").style.background = "#107c10";
    log("✅ Authentification réussie."); await generateMotor(true);
  } catch (e) { alert(`Échec : ${e.message}`); } finally { btn.innerText = "Connexion"; btn.disabled = false; }
});
document.getElementById("btn-generate").addEventListener("click", () => generateMotor(false));

document.getElementById("btn-start").addEventListener("click", () => {
  initAudio();
  if (!currentSessionId) return; if (!checkProbesSafety()) return;
  if (coverOpen) return triggerSecurityAlert("❌ SÉCURITÉ : Refermez le capot !");
  if (lotoState !== 0) return triggerSecurityAlert("❌ SÉCURITÉ : Armoire consignée.");
  if (currentFault) return triggerSecurityAlert("❌ DÉFAUT ACTIF : Réarmez l'installation (Reset) !");
  
  let f1_val = parseFloat(document.getElementById("dim-f1").value);
  if (f1_val < motorConfig.In * 0.95 && currentStartMode !== "vfd") { 
      return triggerSmartFault("thermal_trip", "🛑 ERREUR DIMENSIONNEMENT", `Relais F1 réglé trop bas (${f1_val}A) pour le In du moteur (${motorConfig.In.toFixed(1)}A).`);
  }

  timeInRunPhase = 0; currentStartMode = document.getElementById("start-type").value;
  oscDataI = []; oscDataN = []; 
  playSound('contactor_on');
  api.startSession(currentSessionId, (currentStartMode === "star_delta") ? "star_delta" : "direct").then(updateMeasurementsPanel);
});
document.getElementById("btn-stop").addEventListener("click", () => { initAudio(); if(currentSessionId) { playSound('contactor_off'); api.stopSession(currentSessionId).then(updateMeasurementsPanel); } });

document.getElementById("btn-reset-fault").addEventListener("click", async () => {
  initAudio(); if(!currentAssetId) return; if (!checkProbesSafety()) return;
  clearInterval(pollTimer); playSound('loto'); log("🔄 Purge du système...");
  try {
      const newSession = await api.createSession({ asset_id: currentAssetId });
      currentSessionId = newSession.id; currentSessionState = "stopped"; currentFault = null; timeInRunPhase = 0;
      if(motorPhys.temp > 60) motorPhys.temp = 50.0; 
      log("✅ Réarmement réussi."); updateMeasurementsPanel(newSession);
  } catch(e) { log("❌ Erreur serveur."); } finally { startPolling(); }
});

function startPolling() { if (pollTimer) clearInterval(pollTimer); pollTimer = setInterval(async () => currentSessionId && api.tickSession(currentSessionId, 0.5).then(updateMeasurementsPanel), 500); }