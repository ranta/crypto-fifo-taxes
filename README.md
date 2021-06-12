# Crypto fifo taxes

[![CI](https://github.com/ranta/crypto-fifo-taxes/actions/workflows/ci.yml/badge.svg)](https://github.com/ranta/crypto-fifo-taxes/actions)

A calculator to count gains and losses on crypto mining, staking and trading activities.


### Prerequisites

* [Python 3.8](https://www.python.org/)
* [Poetry](https://github.com/python-poetry/poetry#installation)
* Make


### Setting up a project for development

1. Create a new virtual environment, you can also let Poetry create one for you if you prefer.

2. Create a (preferably PostgreSQL) database for the project.

3. `$ cp .env.template .env` and set your database credentials there.

4. Set up your development environment: `$ make`

### Testing

* Running the tests: `pytest`
* Checking the project test coverage: `pytest --cov`

#### Using Make

Make is used as a convenient build tool.

If you are on Windows and don't have Make, you can get it from:
\
https://community.chocolatey.org/packages/make OR http://gnuwin32.sourceforge.net/packages/make.htm

If you don't want to use Make, you can simply look up the commands from the `Makefile` and use those manually.
