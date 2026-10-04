# VEBITA — Animal Movement Analysis

This is a web app where you upload animal GPS data, pick two algorithms, and compare how well they analyse the movement. It has a backend (Python) and a frontend (website) that both need to be running at the same time.

---

## What you need before starting

- **Python 3.11 or 3.12** — do NOT use 3.13, it will break
- **Node.js** (version 18 or newer)
- A terminal / command prompt

---

## How to run on Mac

### Step 1 — Open Terminal and go to the project folder

```bash
cd "Movement Project"
```

### Step 2 — Run the setup script (first time only)

```bash
bash setup.sh
```

This automatically installs everything for you. Wait for it to finish.

### Step 3 — Start the backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Leave this terminal open.

### Step 4 — Start the frontend (open a new terminal tab)

```bash
cd frontend
npm run dev
```

### Step 5 — Open the app

Go to **http://localhost:5173** in your browser.

---

## How to run on Windows

### Before you start — install these if you don't have them

- Python 3.11 or 3.12 from https://www.python.org/downloads/  
  *(tick "Add Python to PATH" during install)*
- Node.js from https://nodejs.org

---

### Step 1 — Run the setup script (first time only)

**Option A — Command Prompt** (double-click or run from cmd):

```bat
setup.bat
```

**Option B — PowerShell** (more reliable, recommended):

```powershell
.\setup.ps1
```

> If PowerShell blocks the script, run this once first, then retry:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

Both scripts automatically install the Python venv and npm packages. Wait for them to finish.

---

### Step 2 — Start the backend

Open **Command Prompt**:

```bat
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Or **PowerShell**:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Leave this window open.

### Step 3 — Start the frontend (open a new window)

```bat
cd frontend
npm run dev
```

### Step 4 — Open the app

Go to **http://localhost:5173** in your browser.

---

## How to use the app

1. Choose a **service** from the left panel (e.g. "Anomaly Detection")
2. **Upload a CSV** file from Movebank — or just skip this and use the demo data
3. Click **two algorithms** from the list to compare them
4. Click **Run** — results will show up in the tabs at the top (Map, Graphs, F1 Scores, etc.)
5. The **History** tab keeps a record of all your past runs

---

## Common problems

**pip install fails with errors**  
You are probably using Python 3.13. Switch to Python 3.11 or 3.12.

**"Analysis failed" error in the browser**  
The backend is not running. Go back to Step 3 and make sure it started without errors.

**Windows: activate script is blocked**  
Run this once in PowerShell, then retry `.\setup.ps1`:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Project structure

```
Movement Project/
├── backend/        ← Python API (FastAPI)
│   └── vebita_framework/
│       └── services/
│           ├── s1_timeseries/     ← Abdul
│           ├── s2_patterns/       ← Hiba
│           ├── s3_environment/    ← Sarah
│           ├── s4_anomaly/        ← Dua
│           ├── s5_segmentation/   ← Ritika
│           └── s6_classification/ ← Arshan
├── frontend/       ← React website (Vite)
├── setup.sh        ← Mac one-click setup
├── setup.bat       ← Windows one-click setup (Command Prompt)
├── setup.ps1       ← Windows one-click setup (PowerShell, recommended)
└── README.md       ← this file
```
