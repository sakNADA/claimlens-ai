.PHONY: api web test

api:
	uvicorn backend.app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	pytest backend/tests -q

