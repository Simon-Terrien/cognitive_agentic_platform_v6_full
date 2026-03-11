.PHONY: training backend frontend test demo-check verify benchmark start

training:
	cd backend && .venv/bin/uvicorn training_service:app --reload --port 15000

backend:
	cd backend && APP_TRAINING_SERVICE_URL=http://localhost:15000 .venv/bin/uvicorn app.main:app --reload --port 15001

frontend:
	cd frontend && VITE_API_BASE=http://localhost:15001 npm run dev

test:
	cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q

demo-check:
	cd backend && PYTHONPATH=. .venv/bin/python demo_smoke.py

verify: demo-check
	cd frontend && npm run verify

benchmark:
	backend/.venv/bin/python scripts/run_benchmark.py $(filter-out $@,$(MAKECMDGOALS))

start:
	./start.sh $(filter-out $@,$(MAKECMDGOALS))

%:
	@:
