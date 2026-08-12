import { test } from "node:test";
import assert from "node:assert/strict";
import { createApiClient, ApiError } from "../src/apiClient.js";

function mockFetchSequence(responses) {
  let call = 0;
  return async (url, options) => {
    const resp = responses[call];
    call += 1;
    if (!resp) throw new Error(`Appel fetch inattendu #${call} vers ${url}`);
    return {
      ok: resp.status < 400,
      status: resp.status,
      statusText: resp.statusText || "",
      json: async () => resp.body,
    };
  };
}

test("login: stocke le token et l'utilise dans les appels suivants", async () => {
  global.fetch = mockFetchSequence([
    { status: 200, body: { access_token: "fake-token-123", token_type: "bearer" } },
    { status: 201, body: { id: "sess-1", state: "stopped", current_a: 0, voltage_v: 0, simulated_temp_c: 25, fault_active: null } },
  ]);

  const client = createApiClient("http://localhost:8000");
  assert.equal(client.isAuthenticated(), false);

  await client.login("test@vil.com", "secret123");
  assert.equal(client.isAuthenticated(), true);

  const session = await client.createSession({});
  assert.equal(session.id, "sess-1");
});

test("createSession sans authentification préalable lève une erreur claire", async () => {
  global.fetch = mockFetchSequence([]);
  const client = createApiClient("http://localhost:8000");
  await assert.rejects(() => client.createSession({}), /Non authentifié/);
});

test("erreur API (ex: 409) est propagée avec le détail du serveur", async () => {
  global.fetch = mockFetchSequence([
    { status: 200, body: { access_token: "tok" } },
    { status: 409, body: { detail: "Impossible de démarrer depuis l'état 'starting_direct'." } },
  ]);
  const client = createApiClient("http://localhost:8000");
  await client.login("a@b.com", "pw");

  await assert.rejects(
    () => client.startSession("sess-1", "direct"),
    (err) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 409);
      assert.match(err.detail, /Impossible de démarrer/);
      return true;
    }
  );
});

test("registerAndLogin: continue vers login même si register échoue avec 400 (email déjà utilisé)", async () => {
  global.fetch = mockFetchSequence([
    { status: 400, body: { detail: "Cet email est déjà utilisé" } },
    { status: 200, body: { access_token: "tok-existing-user" } },
  ]);
  const client = createApiClient("http://localhost:8000");
  await client.registerAndLogin("existing@vil.com", "secret123");
  assert.equal(client.isAuthenticated(), true);
});

test("registerAndLogin: propage une erreur non-400 de register (ex: 500 serveur)", async () => {
  global.fetch = mockFetchSequence([{ status: 500, body: { detail: "Erreur serveur" } }]);
  const client = createApiClient("http://localhost:8000");
  await assert.rejects(() => client.registerAndLogin("x@vil.com", "pw"), /API error 500/);
});

test("createAsset envoie les données de plaque signalétique et retourne l'asset créé", async () => {
  let capturedBody = null;
  global.fetch = async (url, options) => {
    if (url.endsWith("/login")) return { ok: true, status: 200, json: async () => ({ access_token: "tok" }) };
    capturedBody = JSON.parse(options.body);
    return { ok: true, status: 201, json: async () => ({ id: "asset-1", ...capturedBody }) };
  };
  const client = createApiClient("http://localhost:8000");
  await client.login("a@b.com", "pw");
  const asset = await client.createAsset({
    name: "Moteur test",
    electrical_properties: { rated_power_kw: 1.5 },
    mechanical_properties: { poles: 4 },
  });
  assert.equal(asset.id, "asset-1");
  assert.equal(capturedBody.electrical_properties.rated_power_kw, 1.5);
});

test("generate3DModel appelle le bon endpoint et retourne l'URL du modèle", async () => {
  global.fetch = mockFetchSequence([
    { status: 200, body: { access_token: "tok" } },
    { status: 200, body: { asset_id: "asset-1", model_url: "/api/assets/asset-1/3d-model", file_size_bytes: 38620 } },
  ]);
  const client = createApiClient("http://localhost:8000");
  await client.login("a@b.com", "pw");
  const result = await client.generate3DModel("asset-1");
  assert.equal(result.model_url, "/api/assets/asset-1/3d-model");
  assert.ok(result.file_size_bytes > 0);
});

test("getMotorPhysics retourne les grandeurs électromécaniques calculées", async () => {
  global.fetch = mockFetchSequence([
    { status: 200, body: { access_token: "tok" } },
    { status: 200, body: { synchronous_speed_rpm: 1500, rated_slip: 0.0333, rated_torque_nm: 9.878 } },
  ]);
  const client = createApiClient("http://localhost:8000");
  await client.login("a@b.com", "pw");
  const physics = await client.getMotorPhysics("asset-1");
  assert.equal(physics.synchronous_speed_rpm, 1500);
});

test("generate3DModel propage une erreur 422 si données de plaque manquantes", async () => {
  global.fetch = mockFetchSequence([
    { status: 200, body: { access_token: "tok" } },
    { status: 422, body: { detail: "Données de plaque signalétique manquantes" } },
  ]);
  const client = createApiClient("http://localhost:8000");
  await client.login("a@b.com", "pw");
  await assert.rejects(
    () => client.generate3DModel("asset-incomplet"),
    (err) => {
      assert.ok(err instanceof ApiError);
      assert.equal(err.status, 422);
      return true;
    }
  );
});

test("tickSession envoie bien dt_seconds dans le corps de la requête", async () => {
  let capturedBody = null;
  global.fetch = async (url, options) => {
    if (url.endsWith("/login")) {
      return { ok: true, status: 200, json: async () => ({ access_token: "tok" }) };
    }
    capturedBody = JSON.parse(options.body);
    return {
      ok: true,
      status: 200,
      json: async () => ({ id: "s1", state: "running", current_a: 3.2, voltage_v: 400, simulated_temp_c: 40, fault_active: null }),
    };
  };
  const client = createApiClient("http://localhost:8000");
  await client.login("a@b.com", "pw");
  await client.tickSession("s1", 0.5);
  assert.deepEqual(capturedBody, { dt_seconds: 0.5 });
});
