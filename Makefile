
init:
	pip install poetry --upgrade
	# Updates poetry.lock in case pyproject.toml was updated for install:
	poetry update
	poetry install --no-root --extras test

export PYTHONWARNINGS=ignore::DeprecationWarning
test:
	poetry run py.test

coverage:
	poetry run py.test --verbose --cov-report term --cov=pjrpc tests

check-code:
	pre-commit run --all-file

docs:
	cd docs && make html

.PHONY: docs init test coverage publish check-code
