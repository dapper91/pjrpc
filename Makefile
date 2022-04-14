mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir  := $(dir $(mkfile_path))

init:
	pip install pipenv --upgrade
	pipenv install --dev

.PHONY: test
# https://github.com/aio-libs/aiohttp/issues/3252
# https://stackoverflow.com/questions/879173/how-to-ignore-deprecation-warnings-in-python
export PYTHONWARNINGS=ignore::DeprecationWarning
test:
	@# Either the above or -W ignore::DeprecationWarning. Keep both for information:
	@PYTHONPATH=$(mkfile_dir) pipenv run python -W ignore::DeprecationWarning -m pytest

coverage:
	pipenv run py.test --verbose --cov-report term --cov=xjsonrpc tests

.PHONY: testpypi
testpypi: check-publish-testpypi check-install-testpypi

clean:
	rm -fr build dist .egg xjsonrpc.egg-info

.PHONY: check-setup
CHECK_SETUP_VENV = .venv/check-setup
check-setup: clean
	python3 -m venv $(CHECK_SETUP_VENV)
	source $(CHECK_SETUP_VENV)/bin/activate; \
	python -m pip install --upgrade .[test]; \
	PYTHONPATH=$(mkfile_dir) python -W ignore::DeprecationWarning -m pytest
	$(MAKE) clean

.PHONY: check-publish-testpypi
TESTPYPI_VENV = .venv/check-testpypi
TESTPYPI_IDX  = --index-url https://test.pypi.org/simple
# For the installation of the dependencies from main pypi:
TESTPYPI_IDX += --extra-index-url https://pypi.org/simple
check-publish-testpypi: clean
	pip install --upgrade twine build
	rm -fr build dist .egg xjsonrpc.egg-info
	python -m build
	twine check dist/*
	twine upload --verbose --repository testpypi dist/*
	$(MAKE) clean

check-install-testpypi:
	python3 -m venv $(TESTPYPI_VENV)
	source $(TESTPYPI_VENV)/bin/activate; \
	python -m pip install --upgrade $(TESTPYPI_IDX) xjsonrpc[test]; \
	PYTHONPATH=$(mkfile_dir) python -W ignore::DeprecationWarning -m pytest

publish: clean
	pip install --upgrade twine build
	python setup.py sdist
	python -m build
	twine check dist/*
	twine upload --verbose dist/*
	$(MAKE) clean

check-code:
	pre-commit run --all-file

docs:
	cd docs && make html

.PHONY: docs init test coverage publish check-code
