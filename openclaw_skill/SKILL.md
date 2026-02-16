---
name: MT5 Bridge
description: A skill to interact with MetaTrader 5 running on the Windows host from OpenClaw (WSL).
---

# MT5 Bridge Skill

This skill allows OpenClaw to control MetaTrader 5.

## Prerequisites
- **On Windows**: The `mt5_server.py` must be running.
- **On WSL**: The `mt5_client.py` script (included in this skill) is used to communicate.

## Usage
You can use the `mt5_client.py` script to perform actions.

### API Methods (For AI Agent Use)
The `mt5_client.py` module exposes these helper functions for easy data retrieval:
- `get_account_dict()`: Returns account details (Balance, Equity, etc).
- `get_positions_list()`: Returns list of current open positions.
- `get_history_orders(hours=24)`: Returns list of orders from last N hours.
- `get_history_deals(hours=24)`: Returns list of deals from last N hours.

### Usage Example
```python
import mt5_client
history = mt5_client.get_history_orders(24)
print(history)
```
