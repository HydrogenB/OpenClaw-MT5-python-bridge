# MT5 Python Bridge for OpenClaw

A bridge to control MetaTrader 5 (Windows) from OpenClaw (WSL/Linux) using RPyC.

## Prerequisites

### Windows (Host)
1.  **Python 3.x** installed.
2.  **MetaTrader 5 Terminal** installed and logged in.
3.  Install dependencies:
    ```powershell
    pip install MetaTrader5 rpyc
    ```
4.  **Allow Firewall Rule** (Run PowerShell as Admin):
    ```powershell
    New-NetFirewallRule -DisplayName "OpenClaw MT5 Bridge" -Direction Inbound -LocalPort 18812 -Protocol TCP -Action Allow
    ```

### WSL / Ubuntu (Client)
1.  **Python 3.x** installed.
2.  Install dependencies (Ensure version matches Windows):
    ```bash
    pip3 install rpyc==5.2.3
    ```

## Installation

1.  **Start Server on Windows**:
    ```powershell
    python mt5_server.py
    ```
    *Keep this running in the background.*

2.  **Deploy Skill to OpenClaw (WSL)**:
    Copy the `openclaw_skill` folder to your OpenClaw skills directory:
    ```bash
    cp -r openclaw_skill ~/.openclaw/workspace/skills/mt5-bridge
    ```

## Usage

### Testing Connection
Run the client script from WSL:
```bash
python3 ~/.openclaw/workspace/skills/mt5-bridge/mt5_client.py
```

### Running Full Test Suite (Recommended)
Executes a comprehensive **24-Part Test Suite** covering connection, trading, and real-world TDD scenarios:
```bash
python3 ~/.openclaw/workspace/skills/mt5-bridge/test_scenario.py
```

## Features & Capabilities
The bridge now supports a production-ready feature set:
1.  **Core Trading**: Market, Limit, Stop orders, Modifications, Cancellations, Partial Closes.
2.  **Data Feeds**: Real-time Ticks, OHLC History (M1-MN1), Symbol Info.
3.  **Account**: Balance, Equity, Margin, Leverage, Profit calculations.
4.  **TDD & Safety**:
    -   **Latency Monitoring**: Automatic warnings for high ping.
    -   **Pre-Trade Validation**: Margin checks before sending orders.
    -   **Isolation**: Strict Magic Number filtering for strategy isolation.
    -   **Global Cleanup**: Automated closing of test positions.
5.  **Reconciliation**: Full history analysis including Swaps and Commissions.

## Troubleshooting
- **Connection Refused**: Check Windows Firewall rule. Ensure server is running.
- **Invalid Message Type / Protocol Error**: Check `pip show rpyc` on both machines. They must perfectly match (e.g., both 5.2.3).
- **Pickling Disabled**: Ensure client connects with `config={"allow_pickle": True}`.
- **Empty History**: Ensure you are using `timestamp()` integers for date ranges to avoid timezone issues.
