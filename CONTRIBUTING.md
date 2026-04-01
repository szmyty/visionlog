# Contributing to Visionlog 🤝

Thank you for your interest in contributing to **Visionlog**! We welcome bug reports, feature requests, documentation improvements, and code contributions.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Local Setup](#local-setup)
- [Running Tests](#running-tests)
- [Linting](#linting)
- [Pull Request Workflow](#pull-request-workflow)
- [Code of Conduct](#code-of-conduct)

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:

   ```sh
   git clone https://github.com/<your-username>/visionlog.git
   cd visionlog
   ```

3. Add the upstream remote so you can keep your fork in sync:

   ```sh
   git remote add upstream https://github.com/szmyty/visionlog.git
   ```

---

## Local Setup

Visionlog uses [Poetry](https://python-poetry.org/) for dependency management.

### Prerequisites

- Python ≥ 3.8
- [Poetry](https://python-poetry.org/docs/#installation) installed

### Install dependencies

```sh
poetry install
```

To include optional extras (e.g. tracing or device detection):

```sh
poetry install --extras tracing
poetry install --extras device
# or both at once
poetry install --extras "tracing device"
```

### Activate the virtual environment

```sh
poetry shell
```

---

## Running Tests

Tests are located in the `tests/` directory and use [pytest](https://docs.pytest.org/).

```sh
# Run the full test suite with coverage report
poetry run pytest

# Run a specific test file
poetry run pytest tests/test_logger.py

# Run tests matching a keyword
poetry run pytest -k "test_basic"
```

Coverage results are printed to the terminal after each run. The configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`.

---

## Linting

Visionlog uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```sh
# Check for linting issues
poetry run ruff check .

# Auto-fix fixable issues
poetry run ruff check --fix .

# Check formatting
poetry run ruff format --check .

# Apply formatting
poetry run ruff format .
```

Please ensure there are no linting errors before opening a pull request.

---

## Pull Request Workflow

1. **Create a branch** from `main` with a descriptive name:

   ```sh
   git checkout -b feat/my-new-feature
   # or
   git checkout -b fix/issue-123
   ```

2. **Make your changes**, following the existing code style.

3. **Write or update tests** to cover your changes.

4. **Run linting and tests** to make sure everything passes:

   ```sh
   poetry run ruff check .
   poetry run pytest
   ```

5. **Commit** your changes with a clear, descriptive message:

   ```sh
   git commit -m "feat: add support for custom log formatters"
   ```

6. **Push** your branch to your fork:

   ```sh
   git push origin feat/my-new-feature
   ```

7. **Open a Pull Request** against `main` on the upstream repository. Fill in the PR template with a description of what you changed and why.

8. A maintainer will review your PR. Address any requested changes and push additional commits to your branch.

---

## Code of Conduct

Please review and follow our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive environment for everyone.
