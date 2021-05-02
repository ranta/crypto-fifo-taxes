.PHONY: all install setup

all: install setup

# Install all dependencies and build static files.
install:
	pip install --disable-pip-version-check --upgrade pip
	pip install --upgrade setuptools wheel
	poetry install --no-root

# Set up the database for development.
setup:
	python manage.py migrate
	python manage.py init_project
