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

### Get Account Info
Run the python script to get account information.
```bash
python3 mt5_client.py
```

### Extending functionality
The `mt5_client.py` currently connects and prints account info. You can modify it to accept arguments for specific trades or data retrieval.
