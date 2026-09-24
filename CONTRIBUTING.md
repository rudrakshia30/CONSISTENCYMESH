# Contributing to ConsistencyMesh

Thank you for contributing to ConsistencyMesh! This document provides guidelines and instructions for setting up the development environment, running tests, maintaining code quality, and submitting pull requests.

---

## 1. Prerequisites

Before getting started, ensure you have installed:

- **Python**: Version `3.11` or higher
- **Node.js**: Version `18.x` or higher (with `npm` 9+)
- **Redis** *(optional for local caching and queue features)*: Version 6+ or Redis Docker container
- **Git**: Latest version

---

## 2. Setup Steps

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/CONSISTENCYMESH.git
   cd CONSISTENCYMESH
   ```

2. **Create and activate a virtual environment:**
   - **Linux / macOS:**
     ```bash
     python3.11 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your credentials (such as `GEMINI_API_KEY`).

### Frontend Setup

If working on the frontend:
```bash
cd frontend   # or root directory if unified package.json
npm install
```

---

## 3. Running Tests

### Backend Tests (pytest)

Run the test suite using `pytest`:

```bash
# Run all tests
pytest

# Run with verbose output and coverage report
pytest -v --cov=backend

# Run specific test suites using markers
pytest -m unit
pytest -m integration
pytest -m security
pytest -m performance
```

### Frontend Tests (vitest)

Run frontend component and unit tests:

```bash
# Run tests once
npm test
# or
npx vitest run

# Run in watch mode
npx vitest
```

---

## 4. Linting and Static Analysis

Always ensure your code passes formatting and type checks before committing.

### Python Code Quality

- **Lint checks (Ruff):**
  ```bash
  ruff check .
  ```
- **Auto-fix lint issues:**
  ```bash
  ruff check --fix .
  ```
- **Format check (Ruff):**
  ```bash
  ruff format --check .
  ```
- **Type checking (Mypy):**
  ```bash
  mypy backend
  # or check all project files
  mypy .
  ```

### Frontend Code Quality

```bash
npm run lint
```

---

## 5. Pull Request Guidelines

1. **Create a topic branch:**
   Use descriptive branch prefixes:
   - `feature/feature-name`
   - `fix/bug-fix-name`
   - `docs/documentation-update`
   - `refactor/code-improvement`

2. **Write clean, documented code:**
   - Adhere to PEP 8 / Ruff formatting (100-character line length).
   - Use strict type annotations compatible with Python 3.11+.
   - Add unit/integration tests for any new features or bug fixes.

3. **Verify pre-PR checklist:**
   - [ ] All tests pass (`pytest` and `vitest`).
   - [ ] Ruff checks pass with zero errors (`ruff check .`).
   - [ ] Mypy passes in strict mode (`mypy .`).
   - [ ] Coverage threshold is maintained (minimum 60%).
   - [ ] No secrets or `.env` files are tracked by Git.

4. **Submit Pull Request:**
   - Provide a concise summary of changes and reference relevant issue numbers.
   - Describe verification steps taken.
