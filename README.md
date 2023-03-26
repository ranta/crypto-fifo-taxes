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

---

### Usage

Data is imported to this app with management commands. Below are the available commands with short explanations.

`import_all` -  Import all data from json files and the Binance API.

Accepts the following arguments:
\
`-m` | `--mode` `0|1`. This is only relevant for importing data through the Binance API.

  - `0` = fast mode.
Import trades from only previously known pairs.
  - `1` = full mode. 
Check and import all possible pairs.
Running the command in full mode is extremely slow as the Binance API provides no way to fetch all trades form all pairs.
To actually get the necessary data, we need to check every trade pair individually which uses lots of API weight so the Binance API enforces a cooldown on the API requests.

---

### Testing

* Running the tests: `pytest`
* Checking the project test coverage: `pytest --cov`

---

#### Using Make

Make is used as a convenient build tool.

If you are on Windows and don't have Make, you can get it from:
\
https://community.chocolatey.org/packages/make OR http://gnuwin32.sourceforge.net/packages/make.htm

If you don't want to use Make, you can simply look up the commands from the `Makefile` and use those manually.

---

### Binance API

Create an API key on the [Binance website](https://binance.com) with read permissions and save the API Key
and API Secret to the `.env` file.

---

### Ethplorer API

Ethplorer is used to determine if some ETH deposits were rewards from mining by comparing the sender to a list of mining
pool wallets

Create an Ethplorer account and an API key and save the API Key to the `.env` file.

---

### File importers

It is recommended you back up these files somewhere to prevent data loss

#### Nicehash

Generate a report from Nicehash where you include all of your mining history. Save the `.csv` file to `nicehash_report.csv`

#### Binance ETH2 Staking

**! THIS STEP MAY NO LONGER BE REQUIRED DUE TO UPDATES IN THE BINANCE API**
\
This is required because Binance does not list early ETH2 staking rewards through their API.
However, these rewards can be retrieved through the [Binance website](https://www.binance.com/en/my/earn/history/staking).
Easiest way is to open developer tools and manually copy the returned responses in the network tab to a `binance_eth2_staking.json` file.

#### Coinbase

Trades made in Coinbase. Coinbase does offer an API, but it was deemed not super reliable, because the data might be 
available in Coinbase or Coinbase PRO.  

#### Import JSON

Some transactions are not possible to get through an API. These weird ones can be manually imported through `import.json` file.
You can also override existing transactions in case of incorrect data, e.g. transfers between your wallets and currency swaps
may not be imported properly through the API.

#### Note:

While most transactions can be retrieved through the Binance API, there are some things that Binance doesn't offer
an endpoint for and, which means they need to be imported manually, such as:

- [Convert History](https://www.binance.com/en/my/orders/convert/history)
- [ETH 2.0 Staking (Swapping ETH to BETH)](https://www.binance.com/en/my/saving/history/tokenStaking?tab=2)
- Certain rewards e.g. referrals and [coupons](https://www.binance.com/en/my/coupon)
- Dust to BNB converts in some cases
  - Certain converts are not visible even through [Binance website](https://www.binance.com/en/my/wallet/history/bnbconvert).
    The only way to find details about them is to export Transaction History 3 months at a time to find the converts
    then manually import them to this app. Exporting Transaction History is restricted to 4 times a month and at most
    3 months at a time which makes this a very cumbersome process.
- Any tokens in `Locked Staking` will not be reported in `wallet.get_binance_wallet_balance` due to API Limitations
