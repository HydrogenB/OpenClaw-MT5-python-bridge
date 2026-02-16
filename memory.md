# MT5 Python Bridge Memory

This project creates a communication bridge between OpenClaw (running in WSL/Ubuntu) and MetaTrader 5 (running natively on Windows 11).

## Architecture
- **Protocol**: remote procedure call (RPyC) via TCP/IP.
- **Server (Windows)**:
  - Listens on `0.0.0.0:18812`.
  - Wraps `MetaTrader5` python package.
  - Exposes `exposed_order_send` helper to handle complex dictionary arguments from RPyC.
- **Client (WSL)**:
  - Connects to Windows host IP.
  - Uses `rpyc` to invoke methods on the server.

## Key Configuration Requirements
1. **Firewall Rule (Windows Admin)**:
   ```powershell
   New-NetFirewallRule -DisplayName "OpenClaw MT5 Bridge" -Direction Inbound -LocalPort 18812 -Protocol TCP -Action Allow
   ```
2. **RPyC Version Match**:
   - Both Windows and WSL must run the same RPyC version.
   - We standardized on **`rpyc==5.2.3`**.
   - Mismatch causes `ValueError: invalid message type`.
3. **Pickling Enabled**:
   - Server config: `protocol_config={"allow_pickle": True}`.
   - Client config: `config={"allow_pickle": True}`.
   - Required for passing dictionaries (trade requests) by value.
4. **Data Handling**:
   - On the server side, `rpyc.utils.classic.obtain(request)` is used to explicitly convert RPyC netrefs (proxy objects) into native Python dictionaries for `MetaTrader5` functions.

## Components
- `mt5_server.py`: The Windows server script.
- `openclaw_skill/`: Directory containing the OpenClaw skill package.
  - `mt5_client.py`: The main client script for the skill.
## Test Coverage & TDD
- **Comprehensive Suite**: A 24-part test scenario (`test_scenario.py`) covers:
  1.  **Basics**: Connection, Auth, Ticks, Market Data.
  2.  **Trading**: Ops, Orders, Positions, History.
  3.  **Advanced**: Pending Orders, Expiration, Modification.
  4.  **Real-World TDD**:
      -   **Latency/Freshness**: Checks ping and tick age.
      -   **Risk**: Pre-trade margin validation.
      -   **Safety**: Negative testing (invalid SL/TP), Isolation (Magic IDs).
      -   **Reconciliation**: Profit/Swap/Commission analysis.

## Key Learnings
- **Timezones**: History retrieval requires `datetime.timestamp()` (integers) to avoid RPyC serialization issues and timezone mismatches.
- **Filling Modes**: `mt5.symbol_info(sym).filling_mode` works best with integer bitmask checks (1=FOK, 2=IOC).
- **RPyC**: Must enable `allow_pickle` on both ends for dictionary passing.
