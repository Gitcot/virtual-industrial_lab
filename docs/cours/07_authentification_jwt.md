# 7. Authentification, hashing, JWT

## Ne jamais stocker un mot de passe en clair

```python
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```
`pwd_context` (via `passlib`, algorithme bcrypt) transforme le mot de
passe en une chaîne irréversible. Même si la base de données fuit,
personne ne peut retrouver le mot de passe original (seulement le tester
par force brute, ce que bcrypt rend volontairement lent).

**Bug réel rencontré** : `bcrypt` en version récente (≥4.1) casse la
compatibilité avec `passlib` (`module 'bcrypt' has no attribute
'__about__'`). Le projet pin explicitement `bcrypt==4.0.1` dans
`requirements.txt` — un rappel que les versions de dépendances de sécurité
doivent être testées, pas juste "les plus récentes".

## Vérification (pas déchiffrement)

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```
On ne "déchiffre" jamais un hash bcrypt — on re-hash le mot de passe
fourni et on compare les deux hashs. C'est fondamentalement différent du
chiffrement (réversible) : le hashing est à sens unique par conception.

## JWT (JSON Web Token) — comment ça marche

```python
def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
```
Un JWT est composé de 3 parties encodées en base64, séparées par des
points : `header.payload.signature`. Le `payload` contient ici
`sub` (subject = l'ID utilisateur) et `exp` (expiration). La `signature`
est calculée avec `SECRET_KEY` — **c'est elle qui empêche quiconque de
fabriquer un faux token**, même si le payload est lisible par n'importe
qui (le JWT n'est PAS chiffré, juste signé — ne jamais y mettre de donnée
secrète).

## Vérification côté serveur

```python
def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None
```
Si la signature ne correspond pas (token falsifié) ou si `exp` est dépassé,
`jwt.decode` lève une exception — capturée ici pour retourner `None`
plutôt que de faire planter la requête.

## Pourquoi `SECRET_KEY` ne doit JAMAIS être commitée

```
SECRET_KEY=changeme-generate-a-real-secret   # dans .env.example, valeur factice
```
Si `SECRET_KEY` fuite, n'importe qui peut fabriquer des tokens valides
pour n'importe quel utilisateur. Le guide d'installation demande
explicitement de la régénérer :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
et `.env` (contenant la vraie valeur) est exclu de Git via `.gitignore`.

## Le flux complet dans ce projet

1. `POST /api/auth/register` → hash le mot de passe, crée l'utilisateur
2. `POST /api/auth/login` → vérifie le mot de passe, retourne un JWT
3. Chaque requête protégée envoie `Authorization: Bearer <token>`
4. `get_current_user` (dependency FastAPI) décode le token, retrouve
   l'utilisateur en base, le rend disponible dans la route

## Pour aller plus loin
- jwt.io (décodeur/inspecteur de JWT en ligne, utile pour déboguer)
- OWASP Password Storage Cheat Sheet
