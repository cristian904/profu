# Profu Backend

FastAPI backend for the Profu application.

## Setup

1. Install `uv` if you haven't already:

**Windows (PowerShell - Recommended):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, **restart your terminal** or run:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

**Alternative: Using pip (if you have Python installed):**
```bash
pip install uv
```

After installing with pip, you have several options:

**Option A: Use python -m uv (Recommended - works immediately):**
```bash
python -m uv sync
python -m uv run dev
```

**Option B: Use the wrapper script:**
```bash
# From the backend directory
.\uv.bat sync
.\uv.bat run dev
```

**Option C: Add to PATH manually:**
1. Find your Python Scripts directory:
   ```
   %LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.10_*\LocalCache\local-packages\Python310\Scripts
   ```
   Or run: `python -c "import site; import os; print(os.path.join(site.getusersitepackages().replace('site-packages', ''), 'Scripts'))"`
2. Add it to your User PATH:
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Go to "Advanced" tab → "Environment Variables"
   - Under "User variables", select "Path" → "Edit"
   - Click "New" and paste the Scripts directory path
   - Click OK on all dialogs
   - **Restart your terminal**

**Linux/Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verify installation:**
```bash
uv --version
# Or if not in PATH:
python -m uv --version
```

2. Install dependencies and create virtual environment:
```bash
# If uv is in PATH:
uv sync

# Or use python -m uv:
python -m uv sync

# Or use the wrapper script:
.\uv.bat sync
```

3. Run the server:
```bash
# Development mode (with auto-reload)
uv run dev          # If in PATH
python -m uv run dev  # Or use python -m
.\uv.bat run dev     # Or use wrapper

# Or production mode
uv run start
python -m uv run start
.\uv.bat run start

# Or use the serve alias
uv run serve
python -m uv run serve
.\uv.bat run serve
```

You can also run commands directly:
```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
python -m uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or activate the virtual environment and run directly:
```bash
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## Endpoints

- `GET /` - Health check
- `GET /index` - Returns app description
- `GET /docs` - Interactive API documentation (Swagger UI)
