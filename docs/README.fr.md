# CodeSaver

CodeSaver est un outil en ligne de commande multiplateforme qui crée des instantanés ZIP horodatés de projets de code. Il utilise la bibliothèque standard Python, effectue des sauvegardes en arrière-plan et détecte la langue du système.

## Démarrage rapide

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

Créer une seule sauvegarde sans ouvrir le menu :

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Restaurer une archive :

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

L’intervalle par défaut est de 600 secondes. Utilisez `--no-autosave` pour désactiver la sauvegarde automatique, `--interval 300` pour le modifier et `--language de` pour choisir la langue. `.git`, `__pycache__`, les environnements virtuels et les caches sont exclus par défaut.

Consultez le [README principal](../README.md) pour la documentation complète. Licence MIT.

