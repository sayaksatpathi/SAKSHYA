# Contributing to SAKSHYA

Thanks for your interest in improving SAKSHYA. This guide covers how to set up,
test, and submit changes.

## Development setup

```bash
# Backend
pip install -r requirements-ci.txt      # lean core + test/lint tooling
python -m uvicorn backend.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

FFmpeg/FFprobe must be available on your `PATH`. Optional AI models go in `models/`.

## Before you open a pull request

Run the same checks CI runs — they must pass:

```bash
ruff check backend tests sakshya      # lint (config in ruff.toml)
pytest -q                             # tests
cd frontend && npm run lint && npm run build
```

- **Tests:** add or update tests for any behavior change. Tests that require AI
  models or the external Trust service must `pytest.skip(...)` gracefully when
  the dependency is unavailable (see `tests/test_full_e2e.py` for the pattern).
- **Honesty contract:** never fabricate AI results. A capability without its
  model must report `UNAVAILABLE`. Similarity-based findings are `POSSIBLE_MATCH`.
- **No secrets** in code or fixtures. `SAKSHYA_SECRET_KEY` and credentials come
  from the environment (`.env.example` lists the variables).
- **Commits:** clear, present-tense messages (e.g. `feat(ai): …`, `fix: …`,
  `docs: …`). Keep unrelated changes in separate commits.

## Reporting bugs & requesting features

Open a GitHub issue with steps to reproduce, expected vs actual behavior, and
environment details. For security issues, see [SECURITY.md](SECURITY.md).

## Code of conduct

Be respectful and constructive. Assume good faith and keep discussions focused
on the work.
