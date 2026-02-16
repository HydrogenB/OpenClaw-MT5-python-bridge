import rpyc
import sys
import sys
import os
from datetime import datetime, timezone, timedelta

def get_windows_host_ip():
    """
    Try to detect the Windows host IP address from WSL 2.
    It usually appears as the default gateway in 'ip route'.
    """
    try:
        # Use ip route to find the default gateway
        with os.popen("ip route show | grep default") as f:
            line = f.read().strip()
            if "default via" in line:
                return line.split()[2]
    except Exception:
        pass
    
    # Fallback to localhost if not found
    return "127.0.0.1"

def connect_to_mt5(host=None, port=18812):
    if host is None:
        host = get_windows_host_ip()
    
    try:
        conn = rpyc.connect(host, port, config={"allow_pickle": True})
        return conn
    except Exception as e:
        print(f"Failed to connect to {host}:{port}. Error: {e}")
        return None

def get_account_dict():
    """Returns account info as a clean dictionary."""
    conn = connect_to_mt5()
    if not conn: return {}
    mt5 = conn.root.get_mt5()
    if not mt5.initialize(): return {}
    acct = mt5.account_info()
    if acct is None: return {}
    
    # Manually extract fields to avoid RPyC/Pickle issues
    return {
        "login": int(acct.login),
        "balance": float(acct.balance),
        "equity": float(acct.equity),
        "profit": float(acct.profit),
        "margin": float(acct.margin),
        "margin_free": float(acct.margin_free),
        "leverage": int(acct.leverage),
        "currency": str(acct.currency),
        "server": str(acct.server),
        "company": str(acct.company),
        "trade_allowed": bool(acct.trade_allowed)
    }

def get_positions_list():
    """Returns open positions as a list of dicts."""
    conn = connect_to_mt5()
    if not conn: return []
    mt5 = conn.root.get_mt5()
    if not mt5.initialize(): return []
    positions = mt5.positions_get()
    if positions is None: return []
    
    result = []
    for p in positions:
        result.append({
            "ticket": int(p.ticket),
            "symbol": str(p.symbol),
            "type": int(p.type),  # 0=Buy, 1=Sell
            "volume": float(p.volume),
            "price_open": float(p.price_open),
            "price_current": float(p.price_current),
            "sl": float(p.sl),
            "tp": float(p.tp),
            "profit": float(p.profit),
            "swap": float(p.swap),
            "comment": str(p.comment),
            "time": int(p.time)
        })
    return result

def get_history_orders(hours=168):
    """Returns history orders from last N hours (default 1 week) as list of dicts."""
    conn = connect_to_mt5()
    if not conn: return []
    mt5 = conn.root.get_mt5()
    if not mt5.initialize(): return []
    
    # Use timezone-aware UTC time
    now_utc = datetime.now(timezone.utc)
    from_ts = int(now_utc.timestamp()) - (hours * 3600)
    to_ts = int(now_utc.timestamp()) + 86400 # Future buffer (24h) to cover Server Time offsets
    
    # Use simple timestamps to avoid RPyC datetime issues
    orders = mt5.history_orders_get(from_ts, to_ts)
    if orders is None: return []

    result = []
    for o in orders:
        try:
            result.append({
                "ticket": int(o.ticket),
                "symbol": str(o.symbol),
                "type": int(o.type),
                "state": int(o.state),
                "volume_initial": float(o.volume_initial),
                "volume_current": float(o.volume_current),
                "price_open": float(o.price_open),
                "sl": float(o.sl),
                "tp": float(o.tp),
                "price_current": float(o.price_current),
                "time_setup": int(o.time_setup),
                "time_done": int(o.time_done),
                "comment": str(o.comment)
            })
        except Exception:
             continue # Skip bad records
    return result

def get_history_deals(hours=168):
    """Returns history deals from last N hours (default 1 week) as list of dicts."""
    conn = connect_to_mt5()
    if not conn: return []
    mt5 = conn.root.get_mt5()
    if not mt5.initialize(): return []
    
    now_utc = datetime.now(timezone.utc)
    from_ts = int(now_utc.timestamp()) - (hours * 3600)
    to_ts = int(now_utc.timestamp()) + 86400 # Future buffer (24h)
    
    deals = mt5.history_deals_get(from_ts, to_ts)
    if deals is None: return []

    result = []
    for d in deals:
        try:
            result.append({
                "ticket": int(d.ticket),
                "order": int(d.order),
                "symbol": str(d.symbol),
                "type": int(d.type),
                "entry": int(d.entry), # 0=In, 1=Out
                "volume": float(d.volume),
                "price": float(d.price),
                "profit": float(d.profit),
                "swap": float(d.swap),
                "commission": float(d.commission),
                "time": int(d.time),
                "comment": str(d.comment)
            })
        except Exception:
             continue
    return result

if __name__ == "__main__":
    # Test the helpers
    print("--- Account ---")
    acct = get_account_dict()
    print(acct)
    
    print("\n--- Positions ---")
    pos = get_positions_list()
    print(f"Count: {len(pos)}")
    if pos: print(pos[0])
    
    print("\n--- History Orders (Last 168h) ---")
    orders = get_history_orders(168)
    print(f"Found {len(orders)} orders")
    if orders: print(orders[0])
