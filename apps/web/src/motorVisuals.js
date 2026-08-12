/**
 * Mapping état de simulation (venant de l'API) -> propriétés visuelles 3D.
 * Module volontairement pur (aucune dépendance Three.js/DOM) pour rester
 * testable en isolation, comme le SimulationEngine côté backend.
 */

export const MOTOR_STATES = Object.freeze({
  STOPPED: "stopped",
  STARTING_DIRECT: "starting_direct",
  STARTING_STAR: "starting_star",
  STARTING_DELTA: "starting_delta",
  RUNNING: "running",
  FAULT_THERMAL: "fault_thermal",
  FAULT_ELECTRICAL: "fault_electrical",
  TRIPPED: "tripped",
});

// Couleurs pédagogiques : vert = sain, orange = régime transitoire, rouge = défaut, gris = arrêt
const COLOR_STOPPED = 0x9e9e9e;
const COLOR_STARTING = 0xffa726;
const COLOR_RUNNING = 0x43a047;
const COLOR_FAULT = 0xe53935;
const COLOR_TRIPPED = 0xb0bec5;

/**
 * Retourne la couleur hexadécimale (format Three.js, ex: 0x43a047) à
 * appliquer au matériau du moteur selon son état.
 */
export function getMotorColor(state) {
  switch (state) {
    case MOTOR_STATES.STOPPED:
      return COLOR_STOPPED;
    case MOTOR_STATES.STARTING_DIRECT:
    case MOTOR_STATES.STARTING_STAR:
    case MOTOR_STATES.STARTING_DELTA:
      return COLOR_STARTING;
    case MOTOR_STATES.RUNNING:
      return COLOR_RUNNING;
    case MOTOR_STATES.FAULT_THERMAL:
    case MOTOR_STATES.FAULT_ELECTRICAL:
      return COLOR_FAULT;
    case MOTOR_STATES.TRIPPED:
      return COLOR_TRIPPED;
    default:
      throw new Error(`État moteur inconnu: '${state}'`);
  }
}

/**
 * Retourne la vitesse de rotation angulaire (radians/frame, valeur
 * pédagogique arbitraire pour la lisibilité visuelle, PAS une vitesse
 * physique réelle du moteur) selon l'état.
 */
export function getRotationSpeed(state) {
  switch (state) {
    case MOTOR_STATES.STOPPED:
    case MOTOR_STATES.FAULT_THERMAL:
    case MOTOR_STATES.FAULT_ELECTRICAL:
    case MOTOR_STATES.TRIPPED:
      return 0;
    case MOTOR_STATES.STARTING_DIRECT:
    case MOTOR_STATES.STARTING_DELTA:
      return 0.15; // accélération visible pendant le démarrage
    case MOTOR_STATES.STARTING_STAR:
      return 0.08; // plus lent en étoile (courant réduit -> couple réduit, pédagogique)
    case MOTOR_STATES.RUNNING:
      return 0.2;
    default:
      throw new Error(`État moteur inconnu: '${state}'`);
  }
}

/**
 * Détermine si un halo/pulsation d'alerte doit être affiché (retour visuel
 * fort en cas de défaut, pour la pédagogie "diagnostic").
 */
export function shouldPulseAlert(state) {
  return state === MOTOR_STATES.FAULT_THERMAL || state === MOTOR_STATES.FAULT_ELECTRICAL;
}

/**
 * Convertit la température simulée (°C) en une opacité d'overlay thermique
 * (0 = ambiant, 1 = très chaud), pour un futur rendu type "thermographie
 * simplifiée". Clampé entre 0 et 1.
 */
export function temperatureToHeatOverlay(tempC, ambientC = 25.0, hotC = 100.0) {
  if (hotC <= ambientC) {
    throw new Error("hotC doit être strictement supérieur à ambientC");
  }
  const ratio = (tempC - ambientC) / (hotC - ambientC);
  return Math.min(1, Math.max(0, ratio));
}
