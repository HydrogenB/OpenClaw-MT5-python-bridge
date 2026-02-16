import rpyc
import time
from datetime import datetime, timedelta
import mt5_client

def test_naive_history():
    print("--- Connecting ---")
    conn = mt5_client.connect_to_mt5()
    if not conn:
        return

    mt5 = conn.root.get_mt5()
    if not mt5.initialize():
        print("MT5 Init Failed")
        return

    # Naive request using datetime objects (often problematic with RPyC)
    print("--- Requesting History (Naive) ---")
    now = datetime.now()
    past = now - timedelta(days=5)
    
    try:
        # This often fails if timezones are different or objects aren't pickled right
        orders = mt5.history_orders_get(past, now)
        if orders is None:
             print(f"Orders is None. Error: {mt5.last_error()}")
        else:
             print(f"Retrieved {len(orders)} orders")
             # Try accessing a field
             if len(orders) > 0:
                 print(f"First Order Ticket: {orders[0].ticket}")
                 print(f"First Order Time: {orders[0].time_setup}") # Accessing datetime field
    except Exception as e:
        print(f"❌ CRASHED: {e}")

if __name__ == "__main__":
    test_naive_history()
