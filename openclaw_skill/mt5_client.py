import rpyc
import sys
import os

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
        print(f"Auto-detected Windows Host IP: {host}")
    
    try:
        conn = rpyc.connect(host, port, config={"allow_pickle": True})
        print("Connected to MT5 Service!")
        return conn
    except Exception as e:
        print(f"Failed to connect to {host}:{port}. Error: {e}")
        return None

if __name__ == "__main__":
    conn = connect_to_mt5()
    if conn:
        mt5 = conn.root.get_mt5()
        
        # Example Usage:
        if mt5.initialize():
            print("MT5 Initialized successfully via Bridge")
            print(f"Account Info: {mt5.account_info()}")
            print(f"Terminal Info: {mt5.terminal_info()}")
        else:
            print("MT5 Initialization failed. Check if MT5 is running on Windows.")
            print(f"Last Error: {mt5.last_error()}")
