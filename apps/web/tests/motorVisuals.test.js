import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MOTOR_STATES,
  getMotorColor,
  getRotationSpeed,
  shouldPulseAlert,
  temperatureToHeatOverlay,
} from "../src/motorVisuals.js";

test("getMotorColor: vert pour running", () => {
  assert.equal(getMotorColor(MOTOR_STATES.RUNNING), 0x43a047);
});

test("getMotorColor: rouge pour les deux types de défaut", () => {
  assert.equal(getMotorColor(MOTOR_STATES.FAULT_THERMAL), 0xe53935);
  assert.equal(getMotorColor(MOTOR_STATES.FAULT_ELECTRICAL), 0xe53935);
});

test("getMotorColor: gris pour stopped, gris clair pour tripped (distincts)", () => {
  const stopped = getMotorColor(MOTOR_STATES.STOPPED);
  const tripped = getMotorColor(MOTOR_STATES.TRIPPED);
  assert.notEqual(stopped, tripped);
});

test("getMotorColor: lève une erreur sur état inconnu", () => {
  assert.throws(() => getMotorColor("etat_qui_nexiste_pas"));
});

test("getRotationSpeed: nulle à l'arrêt et en défaut", () => {
  assert.equal(getRotationSpeed(MOTOR_STATES.STOPPED), 0);
  assert.equal(getRotationSpeed(MOTOR_STATES.FAULT_THERMAL), 0);
  assert.equal(getRotationSpeed(MOTOR_STATES.FAULT_ELECTRICAL), 0);
  assert.equal(getRotationSpeed(MOTOR_STATES.TRIPPED), 0);
});

test("getRotationSpeed: le démarrage étoile est plus lent que direct (courant réduit)", () => {
  const star = getRotationSpeed(MOTOR_STATES.STARTING_STAR);
  const direct = getRotationSpeed(MOTOR_STATES.STARTING_DIRECT);
  assert.ok(star < direct, "la vitesse en étoile devrait être visuellement plus faible");
});

test("getRotationSpeed: running tourne (vitesse positive)", () => {
  assert.ok(getRotationSpeed(MOTOR_STATES.RUNNING) > 0);
});

test("shouldPulseAlert: vrai uniquement sur défaut", () => {
  assert.equal(shouldPulseAlert(MOTOR_STATES.FAULT_THERMAL), true);
  assert.equal(shouldPulseAlert(MOTOR_STATES.FAULT_ELECTRICAL), true);
  assert.equal(shouldPulseAlert(MOTOR_STATES.RUNNING), false);
  assert.equal(shouldPulseAlert(MOTOR_STATES.STOPPED), false);
});

test("temperatureToHeatOverlay: 0 à température ambiante", () => {
  assert.equal(temperatureToHeatOverlay(25, 25, 100), 0);
});

test("temperatureToHeatOverlay: 1 à la température chaude de référence", () => {
  assert.equal(temperatureToHeatOverlay(100, 25, 100), 1);
});

test("temperatureToHeatOverlay: valeur intermédiaire cohérente", () => {
  const val = temperatureToHeatOverlay(62.5, 25, 100); // pile au milieu
  assert.ok(Math.abs(val - 0.5) < 1e-9);
});

test("temperatureToHeatOverlay: clampe au-dessus de hotC", () => {
  assert.equal(temperatureToHeatOverlay(500, 25, 100), 1);
});

test("temperatureToHeatOverlay: clampe en dessous de ambientC", () => {
  assert.equal(temperatureToHeatOverlay(-10, 25, 100), 0);
});

test("temperatureToHeatOverlay: lève une erreur si hotC <= ambientC", () => {
  assert.throws(() => temperatureToHeatOverlay(50, 100, 100));
  assert.throws(() => temperatureToHeatOverlay(50, 150, 100));
});
