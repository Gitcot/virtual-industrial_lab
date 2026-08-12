/**
 * Client HTTP vers l'API Virtual Industrial Lab. Volontairement séparé du
 * code DOM/Three.js (main.js) pour rester testable en isolation.
 */

export class ApiError extends Error {
  constructor(status, detail) {
    super(`API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export function createApiClient(baseUrl) {
  let token = null;

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      if (!token) throw new Error("Non authentifié: appelez login() ou register() d'abord.");
      headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetch(`${baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = data.detail || detail;
      } catch {
        /* réponse non-JSON, on garde statusText */
      }
      throw new ApiError(res.status, detail);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return {
    async register(email, password) {
      return request("/api/auth/register", { method: "POST", body: { email, password }, auth: false });
    },
    async login(email, password) {
      const data = await request("/api/auth/login", { method: "POST", body: { email, password }, auth: false });
      token = data.access_token;
      return data;
    },
    async registerAndLogin(email, password) {
      try {
        await this.register(email, password);
      } catch (e) {
        if (!(e instanceof ApiError) || e.status !== 400) throw e; // 400 = email déjà utilisé, on continue vers login
      }
      return this.login(email, password);
    },
    isAuthenticated() {
      return token !== null;
    },
    async createSession(params = {}) {
      return request("/api/simulation/sessions", { method: "POST", body: params });
    },
    async createAsset(params) {
      return request("/api/assets", { method: "POST", body: params });
    },
    async generate3DModel(assetId) {
      return request(`/api/assets/${assetId}/generate-3d-model`, { method: "POST" });
    },
    async getMotorPhysics(assetId) {
      return request(`/api/assets/${assetId}/motor-physics`);
    },
    async getSession(sessionId) {
      return request(`/api/simulation/sessions/${sessionId}`);
    },
    async startSession(sessionId, mode) {
      return request(`/api/simulation/sessions/${sessionId}/start`, { method: "POST", body: { mode } });
    },
    async stopSession(sessionId) {
      return request(`/api/simulation/sessions/${sessionId}/stop`, { method: "POST" });
    },
    async injectFault(sessionId, faultType) {
      return request(`/api/simulation/sessions/${sessionId}/fault`, {
        method: "POST",
        body: { fault_type: faultType },
      });
    },
    async resetSession(sessionId) {
      return request(`/api/simulation/sessions/${sessionId}/reset`, { method: "POST" });
    },
    async acknowledgeSession(sessionId) {
      return request(`/api/simulation/sessions/${sessionId}/acknowledge`, { method: "POST" });
    },
    async tickSession(sessionId, dtSeconds) {
      return request(`/api/simulation/sessions/${sessionId}/tick`, {
        method: "POST",
        body: { dt_seconds: dtSeconds },
      });
    },
  };
}
