# Chalane ka tarika (local run)

Do cheezein alag-alag chalti hain. **Dono terminal khule rehne chahiye.**

| Kaun | Port | Command |
|---|---|---|
| Backend (FastAPI) | 8000 | `uvicorn main:app --reload --port 8000` |
| Frontend (Vite) | 5173 | `npm run dev` |

`localhost:5173` = frontend. `ERR_CONNECTION_REFUSED` uspe aane ka matlab hai Vite
band hai — backend se koi lena-dena nahi.

## Terminal 1 — backend

```powershell
cd D:\SKH-B\SKH-B\backend
python -m venv venv            # sirf pehli baar
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Startup pe yeh chhapega: database path, uploads path, aur kaun-kaun router load hua.

Check karne ke liye:

- <http://127.0.0.1:8000/docs> — saare endpoints, browser se try kar sakte ho
- <http://127.0.0.1:8000/health> — DB reachable hai ya nahi, aur kaun router **fail**
  hua uski wajah ke saath

## Terminal 2 — frontend

```powershell
cd D:\SKH-B\SKH-B
npm install                    # sirf pehli baar
npm run dev
```

Phir <http://localhost:5173> kholo.

Frontend backend ko `http://localhost:8000` pe dhoondta hai (`src/api/client.js`).
Port badalna ho to `SKH-B\.env` mein `VITE_API_URL=http://localhost:8001` daal do —
frontend code chhune ki zaroorat nahi.

## Backend ke bina bhi pura pipeline dekhna ho

```powershell
cd D:\SKH-B\SKH-B\backend
python demo_pipeline.py
```

Yeh throwaway database use karta hai (OS temp folder mein), asli data ko chhuta nahi.

## Triage chalane ka sabse chhota rasta

Triage ko teen cheezein chahiye: tickets, capacity, aur weights. Weights apne aap
seed ho jaate hain (declared default, v1), to bas ye do:

```powershell
# 1. aaj ka budget aur crew-hours (verified_by dena zaroori nahi, par isi se
#    manifest keh sakta hai ki figure pe kisi officer ka naam hai)
curl -X PUT http://localhost:8000/api/triage/capacity ^
  -H "Content-Type: application/json" ^
  -d "{\"budget_inr\": 25000, \"workforce_hours\": 18, \"verified_by\": \"ward_engineer\"}"

# 2. plan banao (budget/workforce chhod do to upar wali stored row use hogi)
curl -X POST http://localhost:8000/api/triage/run ^
  -H "Content-Type: application/json" -d "{}"

# 3. aaj ka manifest
curl http://localhost:8000/api/triage/today
```

`"dry_run": true` bhejo to poora plan wapas aayega par database mein kuch nahi
likhega — "50,000 aur hote to kya hota" isi se dekhte hain.

## "Is ticket ka faisla kyun aisa hua"

Triage chalne ke baad har ticket ka jawab nikal aata hai — scheduled wale ka bhi,
deferred wale ka bhi:

```powershell
# poore run ka review — ek line per ticket, dono bhasha mein citizen sentence
curl http://localhost:8000/api/explain/run/latest

# ek ticket ka pura hisaab: d+/d-, per-criterion contribution, kaun se tickets ne
# uska budget le liya, aur kya badalne se faisla badlega
curl http://localhost:8000/api/explain/<ticket_id>

# sirf wo paragraph jo citizen ko bhejna hai (WhatsApp track isi ko call karega)
curl "http://localhost:8000/api/explain/<ticket_id>/citizen?lang=mr"

# har baar ka record — RTS jawab mein yahi lagta hai
curl http://localhost:8000/api/explain/<ticket_id>/history
```

`run_id` ki jagah `latest` likh sakte ho. Marathi text **machine-drafted** hai,
council ne approve nahi kiya — har response mein `translation_status:
machine_drafted_pending_council_review` isiliye aata hai.

SHAP optional hai: `GET /api/explain/run/latest/shap`. `sklearn`/`shap` install
nahi hain ya cohort chhota hai to 500 nahi, `available: false` + wajah milegi —
exact attribution uske bina bhi poora kaam karta hai.

## Abhi kya kaam nahi karega

`/webhooks/*` — ye router purane SQLAlchemy models import karta hai jo hata diye
gaye. App boot ho jaata hai (ek toota router poori API nahi giraata). WhatsApp
transport teammate ka track hai. `/health` isko naam le kar batata hai.

## Aksar aane wali dikkatein

**`ModuleNotFoundError: No module named 'fastapi'`** — venv activate nahi hua.
Prompt mein `(venv)` dikhna chahiye.

**`Address already in use` / port 8000 busy** — purana uvicorn chal raha hai:
```powershell
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

**`/health` mein `"reachable": false`** — DB file lock ya path galat. Path wahin
chhapta hai; `CRPP_DB_PATH` se badal sakte ho.

**Frontend chal raha hai par data khaali** — backend band hai, ya CORS. Browser
console dekho; `CORS_ORIGINS` default `*` hai.
