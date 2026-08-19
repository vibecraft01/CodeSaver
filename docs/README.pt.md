# CodeSaver

CodeSaver é uma ferramenta multiplataforma de linha de comando que cria snapshots ZIP com data e hora de projetos de código. Usa a biblioteca padrão do Python, executa backups em segundo plano e detecta o idioma do sistema.

## Início rápido

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

Criar um backup sem abrir o menu:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Restaurar um arquivo:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

O intervalo padrão é de 600 segundos. Use `--no-autosave` para desativar o backup automático, `--interval 300` para alterá-lo e `--language de` para escolher o idioma. `.git`, `__pycache__`, ambientes virtuais e caches são excluídos por padrão.

Consulte o [README principal](../README.md) para a documentação completa. Licença MIT.

