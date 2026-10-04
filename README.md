# VEBITA — Animal Movement ML Analysis

A web app for comparing machine learning algorithms on animal GPS tracking data.

---

## How to Run

### Mac

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend (open a new terminal tab):**
```bash
cd frontend
npm install
npm run dev
```

Open your browser at **http://localhost:5173**

---

### Windows

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend (open a new terminal window):**
```bash
cd frontend
npm install
npm run dev
```

Open your browser at **http://localhost:5173**

---

## Notes

- The backend must be running on port 8000 before using the app
- CSV data files are not included in the repo due to file size — add your own to `backend/uploads/`
- Python 3.9+ and Node.js 18+ required
