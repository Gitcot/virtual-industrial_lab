# 13. Conception d'API REST

## Ressources et verbes HTTP

REST modélise une API autour de **ressources** (noms, pas verbes) et de
**verbes HTTP** standards pour les actions :

| Route | Verbe | Signification |
|---|---|---|
| `/api/assets` | GET | lister les assets |
| `/api/assets` | POST | créer un asset |
| `/api/assets/{id}` | GET | lire un asset précis |
| `/api/simulation/sessions/{id}/start` | POST | déclencher une action |

**Point de vigilance** : `/api/simulation/sessions/{id}/start` n'est pas
strictement "RESTful pur" (un puriste dirait qu'il faudrait modéliser
l'action comme une ressource, ex: `POST /sessions/{id}/state-transitions`)
— mais le style "action en verbe" choisi ici est pragmatique et largement
utilisé en pratique quand les actions ne correspondent pas naturellement
à du CRUD (Create/Read/Update/Delete).

## Idempotence — pourquoi ça compte

Une opération est **idempotente** si la répéter plusieurs fois produit le
même résultat qu'une seule fois. `GET`, `PUT`, `DELETE` sont censés
l'être ; `POST` généralement non. Dans ce projet :
- `POST /api/simulation/sessions/{id}/start` n'est PAS idempotent : l'appeler
  deux fois lève une erreur 409 la deuxième fois (comportement voulu — le
  test `test_cannot_start_twice_returns_409` le vérifie explicitement)
- `GET /api/simulation/sessions/{id}` EST idempotent : l'appeler 100 fois
  ne change rien, retourne toujours l'état actuel

## Isolation des ressources par utilisateur

```python
def _get_owned_session(session_id, db, user):
    session = db.query(MotorSession).filter(
        MotorSession.id == session_id,
        MotorSession.owner_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, ...)
```
**Choix délibéré** : retourner 404 (pas trouvé) plutôt que 403 (interdit)
quand un utilisateur essaie d'accéder à la session d'un autre. Révéler
qu'une ressource existe mais est interdite (403) donne une information
que le principe de moindre privilège recommande de ne pas divulguer. Ce
comportement est testé (`test_sessions_are_isolated_per_user`).

## Versionnement d'API (à anticiper, pas encore fait)

Le préfixe actuel est `/api/...`. Quand l'API évoluera de façon
incompatible (breaking change), une pratique courante est de préfixer par
version : `/api/v1/...`, `/api/v2/...`, pour que les anciens clients
continuent de fonctionner. Non encore mis en place dans ce projet — à
introduire avant le premier déploiement public (Phase 11).

## Documentation auto-générée

FastAPI génère automatiquement une documentation interactive à
`/docs` (Swagger UI) à partir des schémas Pydantic et des types de route
— consultable en lançant l'API et en ouvrant
`http://localhost:8000/docs` dans un navigateur. C'est la source de
vérité la plus à jour sur la forme exacte de chaque endpoint (toujours
synchronisée avec le code, contrairement à une documentation écrite à la
main qui peut devenir obsolète).

## Pour aller plus loin
- "REST API Design Rulebook", Mark Massé
- Documentation OpenAPI (le standard que FastAPI génère automatiquement) : https://swagger.io/specification/
