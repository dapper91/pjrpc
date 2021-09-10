"""
Django settings for mysite project.

Generated by 'django-admin startproject' using Django 3.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'pjrpc.server.integration.django',
]

ROOT_URLCONF = 'mysite.urls'
WSGI_APPLICATION = 'mysite.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

JSONRPC_ENDPOINTS = {
    'users': {
        'METHOD_REGISTRY': 'mysite.jsonrpc.users.methods',
        'SPEC': 'mysite.jsonrpc.spec',
        'JSON_ENCODER': 'mysite.jsonrpc.JSONEncoder',
    },
    'posts': {
        'METHOD_REGISTRY': 'mysite.jsonrpc.posts.methods',
        'SPEC': 'mysite.jsonrpc.spec',
        'JSON_ENCODER': 'mysite.jsonrpc.JSONEncoder',
    },
}