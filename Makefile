.PHONY: benchmark-smoke benchmark-api benchmark-android benchmark-test

benchmark-smoke:
	cd backend && python -m app.benchmark run --suite web-smoke

benchmark-api:
	cd backend && python -m app.benchmark run --suite api-smoke

benchmark-android:
	cd backend && python -m app.benchmark run --suite android-smoke

benchmark-test:
	cd backend && python -m pytest tests/test_benchmark_matching.py tests/test_benchmark_runner_security.py tests/test_benchmark_isolation.py -q
