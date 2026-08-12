# 10. Git, GitHub Codespaces, environnement reproductible

## `.gitignore` — ce qui ne doit jamais être versionné

```
__pycache__/
*.pyc
.env
.venv/
*.db
.pytest_cache/
```
- `.env` : contient de vrais secrets (SECRET_KEY, mots de passe DB) — s'il
  était commité, il finirait dans l'historique Git pour toujours, même
  après suppression ultérieure du fichier
- `__pycache__/`, `*.pyc` : fichiers générés automatiquement par Python,
  spécifiques à la machine, inutiles à partager
- `*.db` : bases SQLite locales de test, régénérables

**Erreur fréquente** : committer un `.env` par accident puis le supprimer
— le secret reste visible dans l'historique (`git log`). Si ça arrive, il
faut considérer le secret comme compromis et le régénérer, pas seulement
supprimer le fichier.

## `.env.example` — le contraire de `.env`

`.env.example` (versionné) donne la structure attendue avec des valeurs
factices :
```
SECRET_KEY=changeme-generate-a-real-secret
```
C'est la documentation vivante de "quelles variables d'environnement sont
nécessaires" sans exposer de vrais secrets.

## GitHub Codespaces — pourquoi c'est utile ici

Le master prompt demande un environnement "reproductible" — n'importe qui
(vous, un futur collaborateur) doit pouvoir cloner le dépôt et obtenir
exactement le même environnement de développement, sans "ça marche pas
chez moi parce que j'ai Python 3.9 au lieu de 3.11".

Codespaces lit `.devcontainer/devcontainer.json` et construit
automatiquement cet environnement dans le cloud, accessible depuis un
navigateur — zéro installation locale.

## Convention de commits (recommandation, pas encore imposée dans ce projet)

Une bonne pratique pour la suite : préfixer les messages de commit par
type (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`), par exemple :
```
feat: ajouter le laboratoire moteur (Phase 4)
fix: corriger la constante thermique irréaliste
test: ajouter les tests d'intégration simulation
```
Ça facilite la lecture de l'historique et permet de générer des
changelogs automatiquement plus tard.

## Structure de branches suggérée (à mettre en place)

Pour un projet qui grossit :
- `main` : toujours stable, déployable
- `feature/phase-6-instruments` : une branche par fonctionnalité/phase
- Pull request avant fusion dans `main`, même en solo — ça force une
  relecture à froid du diff complet avant intégration

## Pour aller plus loin
- Documentation Git : https://git-scm.com/doc
- Documentation GitHub Codespaces : https://docs.github.com/codespaces
- Conventional Commits : https://www.conventionalcommits.org/
