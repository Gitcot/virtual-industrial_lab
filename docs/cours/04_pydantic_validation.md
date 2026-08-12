# 4. Pydantic — validation de données

## Le rôle de Pydantic dans ce projet

Chaque donnée qui entre ou sort de l'API passe par un schéma Pydantic. Ce
n'est pas juste du typage décoratif : Pydantic **valide réellement** les
données à l'exécution et rejette ce qui ne correspond pas.

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
```

Si quelqu'un envoie `{"email": "pas-un-email", "password": "x"}`, FastAPI
répond automatiquement avec un 422 détaillant l'erreur — sans une seule
ligne de code de validation écrite à la main.

## `EmailStr` : validation spécialisée

`EmailStr` (nécessite le paquet `email-validator`, présent dans
`requirements.txt`) vérifie que la chaîne a une forme d'email valide. C'est
un exemple de type Pydantic "métier" au-delà des types Python de base
(`str`, `int`...).

## `ConfigDict(from_attributes=True)` — le pont ORM → API

```python
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    ...
```

Sans `from_attributes=True`, Pydantic attend un dictionnaire
(`{"id": ..., "email": ...}`). Avec, il accepte directement un objet
SQLAlchemy (`User`) et lit ses attributs. C'est ce qui permet d'écrire
simplement dans une route :
```python
return user  # objet SQLAlchemy, converti automatiquement en JSON UserOut
```

## Schémas d'entrée vs schémas de sortie — pourquoi les séparer

`UserCreate` (entrée) contient `password` en clair (reçu du client).
`UserOut` (sortie) ne contient PAS de mot de passe, même hashé — cette
séparation empêche par construction une fuite accidentelle de données
sensibles dans une réponse API.

## Validation JSON libre (`dict`)

```python
class AssetCreate(BaseModel):
    electrical_properties: dict = {}
    ...
```

Pour l'Asset (base du futur Digital Twin), les propriétés techniques sont
volontairement un `dict` libre plutôt que des champs typés un par un — le
master prompt exige l'extensibilité (nouveaux paramètres sans migration DB
à chaque fois). C'est un compromis assumé : on perd la validation stricte
de structure interne, on gagne en flexibilité. Un futur raffinement
possible : des sous-schémas Pydantic optionnels pour valider le contenu
JSON quand la structure se stabilisera.

## Erreur fréquente : valeurs par défaut mutables

```python
electrical_properties: dict = {}   # OK avec Pydantic (contrairement aux dataclasses Python pures !)
```
Pydantic gère correctement ce cas en interne (contrairement à une classe
Python classique où `def __init__(self, x={})` partagerait le même dict
entre toutes les instances) — mais c'est un piège classique à connaître
si vous écrivez du Python en dehors de Pydantic (voir cours 1).

## Pour aller plus loin
- Documentation Pydantic v2 : https://docs.pydantic.dev/latest/
- Intégration FastAPI + Pydantic : https://fastapi.tiangolo.com/tutorial/body/
