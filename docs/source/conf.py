# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import sys
from pathlib import Path

import toml

THIS_PATH = Path(__file__).parent
ROOT_PATH = THIS_PATH.parent.parent
sys.path.insert(0, str(ROOT_PATH))

PYPROJECT = toml.load(ROOT_PATH / 'pyproject.toml')
PROJECT_INFO = PYPROJECT['tool']['poetry']

project = PROJECT_INFO['name']
copyright = f"2023, {PROJECT_INFO['name']}"
author = PROJECT_INFO['authors'][0]
release = PROJECT_INFO['version']

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.viewcode',
    'sphinx_copybutton',
    'sphinx_design',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'aiohttp': ('https://aiohttp.readthedocs.io/en/stable/', None),
    'requests': ('https://requests.kennethreitz.org/en/master/', None),
}

autodoc_typehints = 'description'
autodoc_typehints_format = 'short'
autodoc_member_order = 'bysource'
autodoc_default_options = {
    'show-inheritance': True,
}


autosectionlabel_prefix_document = True

html_theme_options = {}
html_title = PROJECT_INFO['name']

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
html_css_files = ['css/custom.css']
