# ERP SaaS Monorepo

## Structure
- `backend/`: Django + Django REST Framework API.
- `frontend/`: Next.js (App Router) frontend.
- `infra/`: deployment artifacts (`docker/`, `nginx/`, `k8s/`).
- `scripts/`: automation helpers.

## Run backend (Django DRF)
```bash
cd erp_saas/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Health endpoint: `GET http://127.0.0.1:8000/api/health/`

## Run frontend (Next.js)
```bash
cd erp_saas/frontend
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:3000`
