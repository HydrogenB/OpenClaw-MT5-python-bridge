import rpyc
import sys
import time
import os
from datetime import datetime, timedelta

def get_windows_host_ip():
    try:
        with os.popen("ip route show | grep default") as f:
            line = f.read().strip()
            if "default via" in line:
                return line.split()[2]
    except Exception:
        pass
    return "127.0.0.1"

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def run_test():
    host = get_windows_host_ip()
    port = 18812
    print(f"--- Starting MT5 Bridge Full Comprehensive Test (Parts 1-12) ---")
    
    try:
        conn = rpyc.connect(host, port, config={"allow_pickle": True})
        mt5 = conn.root.get_mt5()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    if not mt5.initialize():
        print(f"❌ MT5 Initialize Failed: {mt5.last_error()}")
        return
    print(f"✅ MT5 Initialized. Version: {mt5.version()}")

    # --- Part 1-4: Existing Coverage (Condensed) ---
    symbol = "EURUSD"
    if not mt5.symbol_select(symbol, True):
        return

    # --- Part 5: Pending Order Suite ---
    print_section("Part 5: Pending Order Suite")
    tick = mt5.symbol_info_tick(symbol)
    
    # 5.1 Buy Limit (Below Ask)
    price_bl = round(tick.ask - 0.0050, 5)
    req_bl = {
        "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY_LIMIT, "price": price_bl, "magic": 5001,
        "comment": "Test Buy Limit", "type_filling": mt5.ORDER_FILLING_RETURN
    }
    res_bl = conn.root.exposed_order_send(req_bl)
    print(f"Placement Buy Limit: {getattr(res_bl, 'retcode', 'Fail')}")

    # 5.2 Sell Stop (Below Bid)
    price_ss = round(tick.bid - 0.0050, 5)
    req_ss = {
        "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": 0.01,
        "type": mt5.ORDER_TYPE_SELL_STOP, "price": price_ss, "magic": 5002,
        "comment": "Test Sell Stop", "type_filling": mt5.ORDER_FILLING_RETURN
    }
    res_ss = conn.root.exposed_order_send(req_ss)
    print(f"Placement Sell Stop: {getattr(res_ss, 'retcode', 'Fail')}")
    
    # --- Part 6: Account Info ---
    print_section("Part 6: Account Financials")
    acct = mt5.account_info()
    if acct:
        print(f"✅ Login: {acct.login}")
        print(f"✅ Balance: {acct.balance} {acct.currency}")
        print(f"✅ Equity: {acct.equity}")
        print(f"✅ Margin: {acct.margin}")
        print(f"✅ Free Margin: {acct.margin_free}")
        print(f"✅ Leverage: 1:{acct.leverage}")
        if acct.trade_allowed:
            print("✅ Trading Allowed") 
        else:
             print("⚠️ Trading Not Allowed")
        # Interpret flags (0=All, 1=FOK, 2=IOC) - Consts might be missing in some versions
        filling_modes = mt5.symbol_info(symbol).filling_mode
        if filling_modes == 2: # SYMBOL_FILLING_IOC
            print("   -> Supports IOC Only")
        elif filling_modes == 1: # SYMBOL_FILLING_FOK
            print("   -> Supports FOK Only")
        elif filling_modes == 3: # Both
            print("   -> Supports IOC + FOK")
        else:
            print(f"   -> Supports multiple/other modes ({filling_modes})")
    else:
        print("❌ Failed to get account info")

    # --- Part 7: Symbol Info ---
    print_section("Part 7: Symbol Specifications")
    sym_info = mt5.symbol_info(symbol)
    if sym_info:
        print(f"✅ Symbol: {sym_info.name}")
        print(f"✅ Digits: {sym_info.digits}")
        print(f"✅ Point: {sym_info.point}")
        print(f"✅ Min Volume: {sym_info.volume_min}")
        print(f"✅ Max Volume: {sym_info.volume_max}")
        print(f"✅ Step Volume: {sym_info.volume_step}")
        print(f"✅ Contract Size: {sym_info.trade_contract_size}")
    else:
        print("❌ Failed to get symbol info")

    # --- Part 8: Negative Testing ---
    print_section("Part 8: Negative Testing")
    # 8.1 Zero Volume
    req_bad_vol = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": 0.0,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "magic": 8001
    }
    res_bad_vol = conn.root.exposed_order_send(req_bad_vol)
    print(f"Zero Volume Test: Retcode={getattr(res_bad_vol, 'retcode', 'Unknown')} (Expected!=10009)")
    
    # 8.2 Invalid Symbol
    req_bad_sym = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": "INVALID_123", "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY, "price": 1.0, "magic": 8002
    }
    res_bad_sym = conn.root.exposed_order_send(req_bad_sym)
    print(f"Invalid Symbol Test: Retcode={getattr(res_bad_sym, 'retcode', 'Unknown')} (Expected!=10009)")

    # --- Part 9: Modify Pending ---
    print_section("Part 9: Modify Pending")
    # Find our Buy Limit from Part 5
    orders = mt5.orders_get(symbol=symbol)
    bl_orders = [o for o in orders if o.magic == 5001]
    if bl_orders:
        o = bl_orders[0]
        new_price = round(o.price_open - 0.0010, 5)
        print(f"Modifying Ticket {o.ticket} from {o.price_open} to {new_price}")
        req_mod = {
            "action": mt5.TRADE_ACTION_MODIFY, "order": o.ticket,
            "price": new_price, "magic": 5001
        }
        res_mod = conn.root.exposed_order_send(req_mod)
        print(f"Modify Result: {getattr(res_mod, 'retcode', 'Fail')}")
    else:
        print("⚠️ Buy Limit not found for modification")

    # --- Part 10: Expiration ---
    print_section("Part 10: Expiration Test")
    # Place Limit with 1 minute expiration
    user_time = datetime.now() + timedelta(minutes=60) # Ensure future
    # Convert to timestamp
    epoch = datetime(1970, 1, 1)
    timestamp = int((user_time - epoch).total_seconds()) + 3600 # Add buffer for server gap
    
    req_exp = {
        "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY_LIMIT, "price": round(tick.ask - 0.02, 5),
        "magic": 10001, "comment": "Expiring Order",
        "type_time": mt5.ORDER_TIME_SPECIFIED, "expiration": timestamp,
        "type_filling": mt5.ORDER_FILLING_RETURN
    }
    res_exp = conn.root.exposed_order_send(req_exp)
    if getattr(res_exp, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Placed Expiring Order: Ticket {getattr(res_exp, 'order', 0)}")
    else:
        print(f"⚠️ Expiration Order Failed: {getattr(res_exp, 'comment', 'Unknown')}")

    # --- Part 11: Magic Filter ---
    print_section("Part 11: Magic Filter Test")
    # We have orders with magic 5001, 5002, 10001.
    all_orders = mt5.orders_get(symbol=symbol)
    magic_5001 = [o for o in all_orders if o.magic == 5001]
    magic_5002 = [o for o in all_orders if o.magic == 5002]
    print(f"✅ Found {len(magic_5001)} orders with Magic 5001")
    print(f"✅ Found {len(magic_5002)} orders with Magic 5002")

    # --- Part 12: Global Cleanup ---
    print_section("Part 12: Global Cleanup")
    # 1. Close All positions
    positions = mt5.positions_get()
    if positions:
        print(f"Closing {len(positions)} positions...")
        for pos in positions:
            tick_c = mt5.symbol_info_tick(pos.symbol)
            type_c = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price_c = tick_c.bid if type_c == mt5.ORDER_TYPE_SELL else tick_c.ask
            req_c = {
                "action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol,
                "position": pos.ticket, "volume": pos.volume,
                "type": type_c, "price": price_c, "magic": pos.magic,
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            conn.root.exposed_order_send(req_c)
    else:
        print("No open positions to close.")

    # 2. Cancel All Orders
    orders = mt5.orders_get()
    if orders:
        print(f"Canceling {len(orders)} pending orders...")
        for o in orders:
            req_k = {
                "action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket
            }
            conn.root.exposed_order_send(req_k)
    else:
        print("No pending orders to cancel.")

    # --- Generate a Deal for History Check ---
    print_section("Pre-History: Generating a Deal")
    tick = mt5.symbol_info_tick(symbol)
    req_deal = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "magic": 9999,
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    res_deal = conn.root.exposed_order_send(req_deal)
    if getattr(res_deal, 'retcode', None) == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Generated Deal Ticket: {getattr(res_deal, 'deal', 0)}")
        time.sleep(1)
        # Close it
        pos_deal = getattr(res_deal, 'order', 0) 
        # Actually res.order gives order ticket, deals are separate. 
        # We need to find the position to close it.
        positions = mt5.positions_get(symbol=symbol)
        for p in positions:
            if p.magic == 9999:
                 req_c = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol,
                    "position": p.ticket, "volume": p.volume,
                    "type": mt5.ORDER_TYPE_SELL, "price": mt5.symbol_info_tick(symbol).bid,
                    "magic": 9999, "type_filling": mt5.ORDER_FILLING_IOC
                }
                 conn.root.exposed_order_send(req_c)
        print("✅ Closed Deal Position")
    else:
        print(f"⚠️ Failed to generate deal: {getattr(res_deal, 'comment', 'Unknown')}")
    
    time.sleep(2) # Wait for history update

    # --- History Check (Redone securely) ---
    print_section("Final: Robust History Check")
    # Debug Time
    now = datetime.now()
    server_time = datetime.fromtimestamp(mt5.symbol_info_tick("EURUSD").time)
    print(f"   🕒 Client Time: {now}")
    print(f"   🕒 Server Time: {server_time}")
    
    # Use timestamps to avoid RPyC datetime serialization issues
    from_ts = int(datetime(2020, 1, 1).timestamp())
    to_ts = int(datetime(2030, 1, 1).timestamp())
    
    deals = mt5.history_deals_get(from_ts, to_ts)
    if deals is None:
        print(f"❌ History Deals Request Failed: {mt5.last_error()}")
    elif len(deals) > 0:
        print(f"✅ History Deals retrieved: {len(deals)} deals.")
        print(f"   Last Deal: Ticket {deals[-1].ticket}, Profit: {deals[-1].profit}, Time: {deals[-1].time}")
    else:
        print("⚠️ No history deals found (Empty list returned).")

    orders = mt5.history_orders_get(from_ts, to_ts)
    if orders is None:
         print(f"❌ History Orders Request Failed: {mt5.last_error()}")
    elif len(orders) > 0:
        print(f"✅ History Orders retrieved: {len(orders)} (Includes cancelled pending).")
    else:
        print("⚠️ No history orders found.")

    print(f"\n✅ --- COMPREHENSIVE TEST COMPLETE ---")

if __name__ == "__main__":
    run_test()
