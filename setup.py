#!/usr/bin/env python

import pathlib
import setuptools.command.test
import sys
from setuptools import setup, find_packages

requirements = [
]

test_requirements = [
    'aioresponses~=0.0',
    'pytest~=6.0',
    'pytest-aiohttp~=0.0',
    'pytest-mock~=1.0',
    'responses~=0.0',
]

with open('README.rst', 'r') as file:
    readme = file.read()


def parse_about():
    about_globals = {}
    this_path = pathlib.Path(__file__).parent
    about_module_text = pathlib.Path(this_path, 'pjrpc', '__about__.py').read_text()
    exec(about_module_text, about_globals)

    return about_globals


about = parse_about()


class PyTest(setuptools.command.test.test):
    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        setuptools.command.test.test.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.pytest_args))


setup(
    name=about['__title__'],
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    author=about['__author__'],
    author_email=about['__email__'],
    url=about['__url__'],
    license=about['__license__'],
    keywords=[
        'json-rpc', 'rpc', 'jsonrpc-client', 'jsonrpc-server', 'requests', 'aiohttp', 'flask', 'httpx',
    ],
    python_requires=">=3.5",
    packages=find_packages(),
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require={
        'aiohttp': ['aiohttp~=3.0'],
        'aio-pika': ['aio-pika~=6.0'],
        'flask': ['flask~=1.0'],
        'jsonschema': ['jsonschema~=3.0'],
        'kombu': ['kombu~=5.0'],
        'pydantic': ['pydantic~=1.0'],
        'requests': ['requests~=2.0'],
        'httpx': ['requests~=0.0'],
    },
    entry_points={"pytest11": ["pjrpc = pjrpc.client.integrations.pytest"]},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: Public Domain',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    project_urls={
        "Documentation": "https://pjrpc.readthedocs.io/en/latest/",
        'Source': 'https://github.com/dapper91/pjrpc',
    },
    cmdclass={'test': PyTest},
)
