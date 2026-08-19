# Contributing to CodeSaver

Thank you for helping improve CodeSaver. Contributions should keep the project cross-platform, dependency-light, and easy to review.

## Development setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run tests and quality checks before opening a pull request:

```bash
python -m unittest discover -s tests -v
python -m black --check codesaver tests
python -m flake8 codesaver tests
```

New behavior should include tests. User-facing strings belong in `codesaver/lang.py`, and documentation changes should update the relevant language README when practical. Please keep commits focused and describe the user-visible impact in the pull request.

