# CodeSaver

CodeSaver es una herramienta multiplataforma de línea de comandos que crea instantáneas ZIP con fecha y hora de proyectos de código. Utiliza la biblioteca estándar de Python, realiza copias automáticas en segundo plano y detecta el idioma del sistema.

## Inicio rápido

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

Crear una copia sin abrir el menú:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Restaurar un archivo:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

El intervalo predeterminado es de 600 segundos. Usa `--no-autosave` para desactivar las copias automáticas, `--interval 300` para cambiarlo y `--language de` para elegir el idioma. `.git`, `__pycache__`, los entornos virtuales y las cachés se excluyen por defecto.

Consulta el [README principal](../README.md) para obtener toda la documentación. Licencia MIT.

