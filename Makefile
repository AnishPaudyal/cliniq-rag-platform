.PHONY: eval mlflow

eval:
	cd backend && python -m app.evaluation.ragas_eval
	cd backend && python -m app.evaluation.deepeval_suite
	$(MAKE) mlflow

mlflow:
	docker compose up -d mlflow
	@echo "MLflow UI: http://localhost:5000"
