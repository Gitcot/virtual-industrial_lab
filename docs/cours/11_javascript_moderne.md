# 11. JavaScript moderne (client web)

## Modules ES natifs — pas de bundler en Phase 5

```html
<script type="module" src="./src/main.js"></script>
```
```javascript
import { createApiClient, ApiError } from "./apiClient.js";
```
`type="module"` permet au navigateur de comprendre `import`/`export`
nativement, sans outil de build (Webpack, Vite...). C'est volontairement
simple pour la Phase 5 — un vrai bundler viendra probablement plus tard
si le projet grossit (optimisation, minification, découpage de code).

## Import maps — résoudre les paquets npm sans bundler

```html
<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.169.0/build/three.module.js"
  }
}
</script>
```
Sans ça, `import * as THREE from "three"` échouerait dans un navigateur
(un "bare specifier" comme `"three"` n'est pas une URL valide). L'import
map dit explicitement au navigateur "quand tu vois `three`, va chercher
cette URL".

## `async`/`await` — gérer l'asynchrone lisiblement

```javascript
async function login(email, password) {
    const data = await request("/api/auth/login", { method: "POST", body: { email, password } });
    token = data.access_token;
    return data;
}
```
`fetch()` est asynchrone (la réponse HTTP n'arrive pas instantanément).
`await` suspend l'exécution de la fonction jusqu'à ce que la promesse soit
résolue, sans bloquer le reste du navigateur — et sans la pyramide de
callbacks imbriqués du JavaScript pré-2017.

## `fetch` — le client HTTP natif du navigateur

```javascript
const res = await fetch(`${baseUrl}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
});
if (!res.ok) {
    throw new ApiError(res.status, detail);
}
return res.json();
```
**Piège classique** : `fetch` ne lève PAS d'exception sur un code HTTP
d'erreur (404, 500...) — seulement sur une erreur réseau (pas de
connexion). Il faut vérifier `res.ok` explicitement, comme fait ici.

## Classes d'erreur personnalisées

```javascript
export class ApiError extends Error {
    constructor(status, detail) {
        super(`API error ${status}: ${detail}`);
        this.status = status;
        this.detail = detail;
    }
}
```
Étendre `Error` permet de garder le comportement standard (message, stack
trace) tout en ajoutant des champs utiles (`status`, `detail`) que le code
appelant peut inspecter :
```javascript
catch (e) {
    if (e instanceof ApiError) { /* traiter spécifiquement */ }
}
```

## Tester du JS sans framework de test externe

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";

test("login: stocke le token", async () => {
    global.fetch = mockFetchSequence([...]);
    ...
});
```
Depuis Node 18+, `node:test` et `node:assert` sont intégrés — pas besoin
d'installer Jest/Vitest pour des tests simples. `global.fetch = ...`
remplace temporairement la fonction `fetch` réelle par une version
simulée (mock), permettant de tester la logique du client API sans
serveur réel.

## Pour aller plus loin
- MDN, référence JavaScript : https://developer.mozilla.org/fr/docs/Web/JavaScript
- Documentation `node:test` : https://nodejs.org/api/test.html
