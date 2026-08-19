# CodeSaver

CodeSaver は、コードプロジェクトのタイムスタンプ付き ZIP スナップショットを作成するクロスプラットフォームの CLI ツールです。Python 標準ライブラリのみを使用し、バックグラウンドで自動保存を行い、システムの言語を検出します。

## クイックスタート

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

メニューを開かずにバックアップを1つ作成するには:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

アーカイブを復元するには:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

自動保存の既定間隔は 600 秒です。`--no-autosave` で無効化、`--interval 300` で変更、`--language de` で言語を指定できます。`.git`、`__pycache__`、仮想環境、ツールキャッシュは既定で除外されます。

詳しくは[メイン README](../README.md)をご覧ください。ライセンスは MIT です。

