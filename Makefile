.PHONY: training backend frontend test demo-check verify benchmark start \
        up down obs logs ps health clean open

# ── local dev ────────────────────────────────────────────────────────────────

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

# ── docker ───────────────────────────────────────────────────────────────────

## bring the full stack up (build if needed)
up:
	docker compose up --build

## tear down containers (keep volumes)
down:
	docker compose down

## start only the observability trio: prometheus + loki + grafana
obs:
	docker compose up prometheus loki grafana

## tail logs for all services (pass svc=<name> to filter)
logs:
	docker compose logs -f $(svc)

## show container status
ps:
	docker compose ps

## curl every service health endpoint
health:
	@echo "--- training  :15000 ---" && curl -sf http://localhost:15000/api/health | python3 -m json.tool || echo "DOWN"
	@echo "--- backend   :15001 ---" && curl -sf http://localhost:15001/api/health | python3 -m json.tool || echo "DOWN"
	@echo "--- frontend  :15002 ---" && curl -sfo /dev/null -w "%{http_code}\n" http://localhost:15002 || echo "DOWN"
	@echo "--- prometheus:9090  ---" && curl -sfo /dev/null -w "%{http_code}\n" http://localhost:9090/-/healthy || echo "DOWN"
	@echo "--- loki      :3100  ---" && curl -sfo /dev/null -w "%{http_code}\n" http://localhost:3100/ready || echo "DOWN"
	@echo "--- grafana   :3001  ---" && curl -sfo /dev/null -w "%{http_code}\n" http://localhost:3001/api/health || echo "DOWN"

## stop everything AND remove all volumes (destructive)
clean:
	docker compose down -v

## open Grafana in the default browser
open:
	@command -v wslview >/dev/null 2>&1 && wslview http://localhost:3001 \
	  || command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:3001 \
	  || echo "Grafana → http://localhost:3001"

%:
	@:
