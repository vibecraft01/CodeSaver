# CodeSaver

CodeSaver 是一个跨平台命令行工具，可为代码项目创建带时间戳的 ZIP 快照。它仅使用 Python 标准库，在后台执行自动保存，并根据系统设置检测界面语言。

## 快速开始

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

创建一次备份并退出：

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

恢复备份：

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

默认自动保存间隔为 600 秒。使用 `--no-autosave` 禁用自动保存，使用 `--interval 300` 修改间隔，使用 `--language de` 手动指定语言。`.git`、`__pycache__`、虚拟环境和工具缓存默认会被排除。

完整文档请参阅[主 README](../README.md)。许可证：MIT。

