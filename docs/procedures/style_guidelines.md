# Coding Style Guide

As of writing (August 1st 2025), the code owners of this repository should adhere to the [Google Style Guide](https://google.github.io/styleguide/).

**Don't agree with a certain style?** Discuss with the team.

## Deviations from style guide

### Python

#### [Lint with Pylint](https://google.github.io/styleguide/pyguide.html#21-lint)

This repository uses Ruff instead of pylint and Black, for both linting and formatting. `ruff check` includes the stable pylint rules that Ruff implements (`PL`). The configuration, including which rules are selected or ignored and which files are excluded from linting, is under `[tool.ruff]` and `[tool.ruff.lint]` in `pyproject.toml`.

The Ruff workflow (`.github/workflows/lint-ruff.yml`) runs `ruff check .` and `ruff format --check .` on pushes and pull requests that change Python files or `pyproject.toml`. To fix issues locally, run `ruff check --fix .`, which fixes what it can automatically, and `ruff format .`. Use the Ruff version that the workflow installs, since other versions can lint and format differently.

#### [Imports](https://google.github.io/styleguide/pyguide.html#22-imports)

> Use `import` statements for packages and modules only, not for individual types, classes, or functions.

Whereas the above is what should be what's strived for, the code does import types, classes and functions in some locations. For now, this will be left as it is since it avoids some circular imports, but could be looked at a later time.

#### [Line length](https://google.github.io/styleguide/pyguide.html#32-line-length)

The maximum line length in this repository is 100 characters, set by `line-length` in `pyproject.toml`. `ruff format` wraps code to this length where it can, but it does not split long strings, comments or docstrings, and line length is not linted (`E501` is ignored), so some lines are longer.
