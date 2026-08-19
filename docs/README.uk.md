# CodeSaver

CodeSaver — кросплатформна консольна утиліта для створення ZIP-знімків проєктів із вихідним кодом. Вона використовує стандартну бібліотеку Python, виконує автозбереження у фоні та автоматично визначає мову системи.

## Швидкий старт

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

Одноразова резервна копія без меню:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

Відновлення архіву:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

Типовий інтервал автозбереження — 600 секунд. Використовуйте `--no-autosave`, щоб вимкнути його, `--interval 300`, щоб змінити інтервал, і `--language de`, щоб вибрати мову вручну. `.git`, `__pycache__`, віртуальні середовища та кеші інструментів виключаються автоматично.

Повна документація — в [основному README](../README.md). Ліцензія — MIT.

