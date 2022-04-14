mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
mkfile_dir  := $(dir $(mkfile_path))

init:
	pip install pipenv --upgrade
	pipenv install --dev

# https://github.com/aio-libs/aiohttp/issues/3252
# https://stackoverflow.com/questions/879173/how-to-ignore-deprecation-warnings-in-python
export PYTHONWARNINGS=ignore::DeprecationWarning

test:
	@# Either the above or -W ignore::DeprecationWarning. Keep both for information:
	@PYTHONPATH=$(mkfile_dir) pipenv run python -W ignore::DeprecationWarning -m pytest

coverage:
	pipenv run py.test --verbose --cov-report term --cov=xjsonrpc tests

publish:
	pip install twine
	python setup.py sdist
	twine upload dist/*
	rm -fr build dist .egg requests.egg-info

check-code:
	pre-commit run --all-file

docs:
	cd docs && make html

.PHONY: docs init test coverage publish check-code
