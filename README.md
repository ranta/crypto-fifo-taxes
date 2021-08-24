# Crypto fifo taxes

[![CI](https://github.com/ranta/crypto-fifo-taxes/actions/workflows/ci.yml/badge.svg)](https://github.com/ranta/crypto-fifo-taxes/actions)

A calculator to count gains and losses on crypto mining, staking and trading activities.


### Prerequisites

* [Python 3.8](https://www.python.org/)
* [Poetry](https://github.com/python-poetry/poetry#installation)
* Make
* PostgreSQL


### Setting up a project for development

1. Create a new virtual environment, you can also let Poetry create one for you if you prefer.

2. Create a PostgreSQL database for the project.

3. Run `$ cp .env.template .env` and set up your database credentials there.

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

### Using the Binance API

Create an API key on the [Binance website](https://binance.com) with read permissions and save the API Key
and API Secret to the `.env` file.

#### Note:

While most transactions can be retrieved through the Binance API, there are some things that Binance doesn't offer
an endpoint for and, which means they need to be imported manually, such as:

- [Convert History](https://www.binance.com/en/my/orders/convert/history)
- [ETH 2.0 Staking (Swapping ETH to BETH)](https://www.binance.com/en/my/saving/history/tokenStaking?tab=2)
- Certain rewards e.g. referrals and [coupons](https://www.binance.com/en/my/coupon)
- Dust to BNB converts in same cases
  - Certain converts are not visible even through [Binance website](https://www.binance.com/en/my/wallet/history/bnbconvert).
    The only way to find details about them is to export Transaction History 3 months at a time to find the converts
    then manually import them to this app. Exporting Transaction History is restricted to 4 times a month and at most
    3 months at a time which makes this a very cumbersome process.
