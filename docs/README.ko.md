# CodeSaver

CodeSaver는 코드 프로젝트의 타임스탬프 ZIP 스냅샷을 만드는 크로스 플랫폼 CLI 도구입니다. Python 표준 라이브러리만 사용하며 백그라운드 자동 저장과 시스템 언어 감지를 지원합니다.

## 빠른 시작

```bash
python -m venv .venv
python -m pip install -e .
codesaver
```

메뉴 없이 백업 하나 만들기:

```bash
codesaver --project-dir ./my-project --backup-dir ./backups --backup-now
```

아카이브 복원하기:

```bash
codesaver --project-dir ./my-project --restore ./backups/my-project_2026-01-20_14-30-00.zip --overwrite
```

기본 자동 저장 간격은 600초입니다. `--no-autosave`로 비활성화하고, `--interval 300`으로 변경하며, `--language de`로 언어를 지정할 수 있습니다. `.git`, `__pycache__`, 가상 환경과 도구 캐시는 기본적으로 제외됩니다.

전체 문서는 [기본 README](../README.md)를 참고하세요. 라이선스는 MIT입니다.

