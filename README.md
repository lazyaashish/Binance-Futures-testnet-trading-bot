# Binance Futures Testnet Trading Bot

A lightweight Python CLI app for placing orders on the Binance USDT-M Futures Testnet.

It supports Market, Limit, and Stop-Limit orders, validates CLI input, logs API requests and responses, and separates the REST client from order and command-line logic.

## Project Structure

```text
trading_bot/
|-- bot/
|   |-- __init__.py
|   |-- client.py            # HMAC-signed Binance REST client
|   |-- orders.py            # Market, Limit, and Stop-Limit order methods
|   |-- validators.py        # CLI input validation
|   `-- logging_config.py    # File and console logging
|-- tests/
|   |-- __init__.py
|   `-- test_bot.py
|-- cli.py                   # argparse CLI entry point
|-- .env.example             # Credential template
|-- .gitignore
|-- requirements.txt
`-- README.md
```

## Setup

### 1. Create Binance Futures Testnet Credentials

1. Open [https://testnet.binancefuture.com](https://testnet.binancefuture.com).
2. Sign in with your GitHub account.
3. Open **API Key** from the top-right menu.
4. Generate an API key and secret. Copy the secret immediately.

This app always targets:

```text
https://testnet.binancefuture.com
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Credentials

Copy the template:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

Never commit `.env`. It is already ignored by `.gitignore`.

## Usage

General syntax:

```bash
python cli.py --symbol SYMBOL --side BUY|SELL --type MARKET|LIMIT|STOP_LIMIT --quantity QTY [options]
```

Options:

| Flag | Required | Description |
| --- | --- | --- |
| `--symbol`, `-s` | Yes | Trading pair, for example `BTCUSDT` |
| `--side` | Yes | `BUY` or `SELL` |
| `--type`, `-t` | Yes | `MARKET`, `LIMIT`, or `STOP_LIMIT` |
| `--quantity`, `-q` | Yes | Order quantity, for example `0.001` |
| `--price`, `-p` | Limit and Stop-Limit | Limit price |
| `--stop-price` | Stop-Limit | Trigger price |
| `--api-key` | No | Overrides `BINANCE_API_KEY` |
| `--api-secret` | No | Overrides `BINANCE_API_SECRET` |
| `--log-dir` | No | Log directory, defaults to `logs` |
| `--yes`, `-y` | No | Skip the confirmation prompt |

## Examples

Market BUY:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

Market SELL without confirmation:

```bash
python cli.py --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01 --yes
```

Limit BUY:

```bash
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 60000
```

Limit SELL:

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000
```

Stop-Limit BUY:

```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.001 --price 95000 --stop-price 94500
```

Pass credentials inline:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --api-key YOUR_KEY --api-secret YOUR_SECRET --yes
```

## Sample Output

```text
======================================================
  ORDER REQUEST SUMMARY
======================================================
  Symbol        : BTCUSDT
  Side          : BUY
  Order Type    : MARKET
  Quantity      : 0.001
======================================================

  Proceed with this order? [y/N]: y

Sending order to Binance Futures Testnet...

SUCCESS: order placed
------------------------------------------------------
  Order ID        : 3426505863
  Symbol          : BTCUSDT
  Status          : FILLED
  Side            : BUY
  Type            : MARKET
  Orig Qty        : 0.001
  Executed Qty    : 0.001
  Avg / Limit Price: 96342.50
  Time In Force   : GTC
------------------------------------------------------
Log: logs/trading_bot_20260521.log
```

## Tests

Run the unit tests:

```bash
pytest tests/ -v
```

The tests cover validation, request signing, network error handling, API error wrapping, and order payload construction. They don't require live Binance credentials.

## Logging

Logs are written to:

```text
logs/trading_bot_YYYYMMDD.log
```

File logs include DEBUG-level request and response details. Console logs only show warnings and errors so the CLI output stays readable.

This repository includes `logs/sample_market_limit_orders.log` as a mock sample showing the expected log format for one Market order and one Limit order. It's not evidence of a live testnet execution.

Security notes:

- API signatures are redacted from request logs.
- API secrets are never logged.
- API keys shown in startup logs are partially redacted.
##temp data to be cleared
## Error Handling

The app handles:

- Missing credentials
- Invalid input such as bad side, unsupported order type, non-positive quantity, or missing limit price
- Binance API errors with returned code and message
- Network failures and timeouts
- Unexpected exceptions, with full details written in log files
## Assumptions

- This app is for Binance USDT-M Futures Testnet only, not live trading.
- Quantities and prices are validated as positive numbers locally. Exchange-specific precision, step-size, and min-notional rules are enforced by Binance.
- Stop-Limit uses Binance Futures order type `STOP` under the hood.
- `timeInForce` defaults to `GTC` for Limit and Stop-Limit orders.
- Testnet balances are virtual

## License

MIT
