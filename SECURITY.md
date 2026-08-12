# Sécurité — Virtual Industrial Lab

## Principes appliqués (Core actuel)
- Mots de passe hashés avec bcrypt (jamais en clair)
- Authentification par JWT signé (HS256), expiration configurée
- Secrets hors dépôt (.env non versionné, .env.example fourni)
- Requêtes DB paramétrées via ORM SQLAlchemy (protection injection SQL)
- CORS restrictif (origines explicites, à ajuster en production)
- Validation stricte des entrées via Pydantic

## À faire avant mise en production (non couvert par ce Core)
- HTTPS/TLS obligatoire
- Rate limiting sur /api/auth/login et /api/auth/register
- Rotation des secrets
- RBAC complet (le champ `role` existe mais n'est pas encore vérifié dans les routes)
- Scan des dépendances (ex: pip-audit, Dependabot)
- Sécurité Docker/CI (images minimales, scan de vulnérabilités)
- Journalisation sans secrets, sauvegardes/restauration testées

## Signaler une vulnérabilité
À définir selon votre processus interne.
