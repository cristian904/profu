# Profu Backend

FastAPI backend for the Profu application.

## Setup

### 1. Install Poetry

**Windows (PowerShell):**
```powershell
pip install poetry
```

Or use the official installer:
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

**Verify installation:**
```bash
python -m poetry --version
```

### 2. Install Dependencies

```bash
cd backend
python -m poetry install
```

This will create a `.venv` folder in the project directory.

### 3. Run the Server

**Option 1: Use Poetry run (Recommended - No activation needed):**
```bash
python -m poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Option 2: Use the helper script:**
```powershell
.\run.ps1
```

**Option 3: Activate virtual environment (if execution policy allows):**
```powershell
# If you get execution policy error, use the helper script:
.\activate.ps1

# Or use Command Prompt instead:
.venv\Scripts\activate.bat
```

**Option 4: Use Command Prompt (CMD) - No execution policy issues:**
```cmd
cd backend
.venv\Scripts\activate.bat
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Quick Start

```bash
cd backend
python -m poetry install
python -m poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## Endpoints

- `GET /` - Health check
- `GET /index` - Returns app description
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Fixing PowerShell Execution Policy

If you get an execution policy error when activating the venv:

**Option 1: Use Poetry run (No activation needed)**
```bash
python -m poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Option 2: Use the helper script**
```powershell
.\activate.ps1
```

**Option 3: Change execution policy (Requires Admin PowerShell)**
```powershell
# Run PowerShell as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Option 4: Use Command Prompt instead**
CMD doesn't have execution policy restrictions.

## Adding Dependencies

```bash
python -m poetry add package-name
python -m poetry add --group dev package-name
```
