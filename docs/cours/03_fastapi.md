# 3. FastAPI — le framework web du backend

## Pourquoi FastAPI (et pas Flask/Django)
- Validation automatique des entrées/sorties via Pydantic (voir cours 4)
- Documentation interactive générée automatiquement (`/docs`)
- Asynchrone par nature (utile pour des I/O comme la DB, plus tard des
  websockets pour le temps réel)
- Type hints natifs → moins d'erreurs, meilleure autocomplétion IDE

## Anatomie d'une route (extrait réel : `auth.py`)

```python
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)
```

Décomposition :
- `@router.post("/login", ...)` : associe la fonction à `POST /api/auth/login`
- `payload: LoginRequest` : FastAPI lit le corps JSON de la requête, le
  valide contre le schéma Pydantic `LoginRequest`, et le passe déjà
  converti en objet Python — sans code de parsing manuel
- `db: Session = Depends(get_db)` : **injection de dépendances** (voir plus
  bas)
- `response_model=Token` : FastAPI valide aussi ce que la fonction
  retourne, et génère la documentation OpenAPI en conséquence

## Injection de dépendances (`Depends`)

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Ce `yield` (plutôt que `return`) est ce qu'on appelle un générateur : le
code avant `yield` s'exécute au début de la requête, le code après
(`db.close()`) s'exécute automatiquement à la fin — **même si une
exception est levée entre-temps**. C'est ce qui garantit qu'on ne fuit
jamais de connexions DB non fermées.

`get_current_user` (dans `app/api/deps.py`) fait la même chose pour
l'authentification :
```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    ...
```
Une dépendance peut elle-même dépendre d'une autre dépendance — FastAPI
résout la chaîne automatiquement.

## Codes de statut HTTP utilisés dans ce projet et pourquoi

| Code | Utilisé pour | Exemple dans le projet |
|---|---|---|
| 200 | Succès (lecture, action) | `GET /api/auth/me` |
| 201 | Création réussie | `POST /api/auth/register` |
| 400 | Requête invalide côté client (donnée métier) | Email déjà utilisé |
| 401 | Authentification manquante/invalide | Token absent ou expiré |
| 404 | Ressource introuvable | Asset ou session inexistante |
| 409 | Conflit d'état | Tenter de démarrer un moteur déjà démarré |
| 422 | Erreur de validation | `mode` invalide dans `/start` |

**Point de vigilance** : 400 vs 422 vs 409 sont souvent confondus. Règle
utilisée ici : 422 = la structure des données est fausse (Pydantic
l'attrape automatiquement) ; 400/409 = la structure est correcte mais
l'action est métier-invalide (c'est le code applicatif qui décide).

## CORS (Cross-Origin Resource Sharing)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    ...
)
```
Sans ça, le navigateur bloquerait les appels du client web (port 5173)
vers l'API (port 8000) — deux "origines" différentes du point de vue du
navigateur. **Erreur fréquente** : mettre `allow_origins=["*"]` en
production avec `allow_credentials=True` — combinaison interdite par les
navigateurs modernes pour de bonnes raisons de sécurité.

## Pour aller plus loin
- Documentation officielle : https://fastapi.tiangolo.com/
- Tutoriel dependency injection : https://fastapi.tiangolo.com/tutorial/dependencies/
