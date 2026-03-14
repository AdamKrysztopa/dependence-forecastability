# 7. Engineering Rules

- [x] Target Python `3.11`.
- [x] Add type hints across all modules.
- [x] Use Google-style docstrings on public functions/classes.
- [x] Avoid blind `except Exception`; catch specific exceptions only.
- [x] Keep cognitive complexity `<= 7` per function where possible.
- [x] Extract helper logic into private `_` functions.
- [x] Do not use boolean positional arguments; use keyword-only arguments.
- [x] Keep `try` blocks narrow around only the raising call.
- [x] Use deterministic random state handling (`int` seed).
- [x] Use dataclasses or Pydantic models for result containers.
- [x] Save all artifacts under `outputs/`.
- [x] Drive reproducibility via YAML config files (avoid hardcoded constants).
