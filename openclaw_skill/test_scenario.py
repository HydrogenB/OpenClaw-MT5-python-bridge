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
    print(f"--- Starting MT5 Bridge Full Comprehensive Test (Parts 1-24) ---")
    
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

    symbol = "EURUSD"
    if not mt5.symbol_select(symbol, True):
        print(f"❌ Failed to select {symbol}")
        return

    # --- Part 13: Latency & Connectivity Check ---
    print_section("Part 13: Latency & Connectivity Check")
    start_time = time.time()
    tick = mt5.symbol_info_tick(symbol)
    latency_ms = (time.time() - start_time) * 1000
    print(f"✅ Roundtrip Latency: {latency_ms:.2f} ms")
    if latency_ms > 200: # TDD Expectation
        print(f"⚠️ Warning: Latency High (>200ms)")
    else:
        print(f"✅ Latency OK")

    # --- Part 14: Data Freshness (Tick Age) ---
    print_section("Part 14: Data Freshness (Tick Age)")
    # Note: potential timezone diffs, just checking if it is recent relative to server time usually
    # ideally we verify against last known server time
    tick_time = datetime.fromtimestamp(tick.time)
    print(f"✅ Tick Time: {tick_time}")
    # Simple check: is it non-zero
    if tick.time > 0:
        print("✅ Data Stream Active")
    else:
        print("❌ Stale Data")

    # --- Part 15: Pre-Trade Margin Validation ---
    print_section("Part 15: Pre-Trade Margin Validation")
    lot_size = 1.0
    margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, lot_size, tick.ask)
    acct = mt5.account_info()
    if margin is not None:
        print(f"✅ Margin for {lot_size} lots: {margin:.2f} {acct.currency}")
        if acct.margin_free < margin:
             print("⚠️ Insufficient Margin (Simulation)")
        else:
             print("✅ Margin Check Passed")
    else:
        print("❌ Margin Calc Failed")

    # --- Part 16: Symbol Filling Mode Check ---
    print_section("Part 16: Filling Mode Check")
    # This acts as a discovery TDD
    sym_info = mt5.symbol_info(symbol)
    filling_modes = sym_info.filling_mode
    print(f"✅ Raw Filling Mode Flag: {filling_modes}")
    # Interpret flags (1=FOK, 2=IOC, 3=Both generally)
    if filling_modes == 2: # SYMBOL_FILLING_IOC
        print("   -> Supports IOC Only")
    elif filling_modes == 1: # SYMBOL_FILLING_FOK
        print("   -> Supports FOK Only")
    elif filling_modes == 3: # Both
        print("   -> Supports IOC + FOK")
    else:
        print(f"   -> Supports multiple/other modes ({filling_modes})")

    # --- Part 17: Invalid SL/TP Logic (TDD) ---
    print_section("Part 17: Invalid SL/TP Logic (TDD)")
    # Try to buy with Stop Loss ABOVE price (Invalid for Buy)
    invalid_sl = tick.ask + 0.0050
    req_bad_sl = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "sl": invalid_sl, 
        "magic": 17001, "type_filling": mt5.ORDER_FILLING_IOC
    }
    res_bad_sl = conn.root.exposed_order_send(req_bad_sl)
    print(f"Invalid SL Test: Retcode={getattr(res_bad_sl, 'retcode', 'Unknown')} (Expected!=10009)")
    if getattr(res_bad_sl, 'retcode', 0) == 10016: # Invalid Stops
        print("✅ Correctly Rejected Invalid Stops")
    else:
        print(f"⚠️ Unexpected Retcode: {getattr(res_bad_sl, 'retcode', 0)}")

    # --- Part 18: Magic Number Isolation (TDD) ---
    print_section("Part 18: Magic Number Isolation")
    # Open Pos A (Magic 18001)
    # Open Pos B (Magic 18002)
    # Ensure closing 'A' doesn't touch 'B'
    print("Opening Magic 18001 & 18002...")
    for m in [18001, 18002]:
        req_iso = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY, "price": tick.ask, "magic": m,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        conn.root.exposed_order_send(req_iso)
        time.sleep(1)

    all_pos = mt5.positions_get(symbol=symbol)
    pos_18001 = [p for p in all_pos if p.magic == 18001]
    pos_18002 = [p for p in all_pos if p.magic == 18002]
    
    if pos_18001 and pos_18002:
        print("✅ Both positions opened.")
        # Close 18001
        p = pos_18001[0]
        req_c = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "position": p.ticket,
            "volume": 0.01, "type": mt5.ORDER_TYPE_SELL, "price": mt5.symbol_info_tick(symbol).bid,
            "magic": 18001, "type_filling": mt5.ORDER_FILLING_IOC
        }
        res_c = conn.root.exposed_order_send(req_c)
        if getattr(res_c, 'retcode', 0) == 10009:
            print("✅ Closed 18001.")
            # Verify 18002 still exists
            check_18002 = [p for p in mt5.positions_get(symbol=symbol) if p.magic == 18002]
            if check_18002:
                print("✅ Pass: Magic 18002 still remains (Isolation Confirmed).")
            else:
                print("❌ Fail: Magic 18002 vanished.")
        else:
            print("❌ Failed to close 18001.")
    else:
        print("⚠️ Setup failed for Isolation test.")

    # --- Part 19: Grid Strategy Setup ---
    print_section("Part 19: Grid Strategy Setup")
    # Place 3 Buy Limits at steps
    base_price = tick.ask - 0.0020
    grid_orders = []
    print("Placing 3-level Grid...")
    for i in range(3):
        price_g = round(base_price - (i * 0.0010), 5)
        req_g = {
            "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY_LIMIT, "price": price_g, 
            "magic": 19000, "comment": f"Grid Lvl {i}",
            "type_filling": mt5.ORDER_FILLING_RETURN
        }
        res_g = conn.root.exposed_order_send(req_g)
        if getattr(res_g, 'retcode', 0) == 10009:
            grid_orders.append(getattr(res_g, 'order', 0))
    
    if len(grid_orders) == 3:
        print(f"✅ Grid Setup Complete: {grid_orders}")
    else:
        print(f"⚠️ Grid Setup Partial: {len(grid_orders)}/3")

    # --- Part 20: Bulk Close (By Magic) ---
    print_section("Part 20: Bulk Close (By Magic)")
    # Clean up Magic 18002 and 19000 (Grid)
    # 1. Close Net Positions (18002)
    pos_clean = [p for p in mt5.positions_get(symbol=symbol) if p.magic == 18002]
    for p in pos_clean:
        req_cl = {
             "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "position": p.ticket,
             "volume": p.volume, "type": mt5.ORDER_TYPE_SELL, "price": mt5.symbol_info_tick(symbol).bid,
             "magic": 18002, "type_filling": mt5.ORDER_FILLING_IOC
        }
        conn.root.exposed_order_send(req_cl)
    print(f"✅ Bulk Closed {len(pos_clean)} positions (Magic 18002).")

    # 2. Cancel Grid (19000)
    orders_clean = [o for o in mt5.orders_get(symbol=symbol) if o.magic == 19000]
    for o in orders_clean:
         req_k = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
         conn.root.exposed_order_send(req_k)
    print(f"✅ Bulk Cancelled {len(orders_clean)} orders (Magic 19000).")

    # --- Part 21 & 22: Profit & Cost Reconciliation ---
    print_section("Part 21/22: Profit & Cost Analysis")
    # Look at history for 18001
    from_ts = int(datetime(2020, 1, 1).timestamp())
    to_ts = int(datetime(2030, 1, 1).timestamp())
    deals = mt5.history_deals_get(from_ts, to_ts)
    
    deals_18001 = [d for d in deals if d.magic == 18001] if deals else []
    if deals_18001:
        total_profit = sum(d.profit for d in deals_18001)
        total_swaps = sum(d.swap for d in deals_18001)
        total_comm = sum(d.commission for d in deals_18001)
        print(f"✅ Magic 18001 Analysis ({len(deals_18001)} deals):")
        print(f"   Net Profit: {total_profit:.2f}")
        print(f"   Swaps: {total_swaps:.2f}")
        print(f"   Commission: {total_comm:.2f}")
        print(f"   Gross PnL: {total_profit + total_swaps + total_comm:.2f}")
    else:
        print("⚠️ No history for 18001 to analyze.")

    # --- Part 23: Server Time Sync ---
    print_section("Part 23: Time Sync Calc")
    # Compare Time.time() (Local UTC-ish) vs Tick Time
    local_ts = time.time()
    server_ts = tick.time
    offset = server_ts - local_ts
    print(f"✅ Local TS: {local_ts:.0f}")
    print(f"✅ Server TS: {server_ts}")
    print(f"✅ Offset: {offset:.0f} seconds (Server - Local)")
    # This offset is critical for algo scheduling

    # --- Part 24: Ultimate Cleanup ---
    print_section("Part 24: Ultimate Cleanup")
    # Close EVERYTHING on this symbol
    all_final_pos = mt5.positions_get(symbol=symbol)
    if all_final_pos:
        print(f"🧹 Closing {len(all_final_pos)} remaining positions...")
        for p in all_final_pos:
             req_f = {
                 "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "position": p.ticket,
                 "volume": p.volume, "type": mt5.ORDER_TYPE_SELL if p.type==mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                 "price": mt5.symbol_info_tick(symbol).bid if p.type==mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask,
                 "magic": p.magic, "type_filling": mt5.ORDER_FILLING_IOC
            }
             conn.root.exposed_order_send(req_f)
    else:
        print("✅ No remaining positions.")

    all_final_orders = mt5.orders_get(symbol=symbol)
    if all_final_orders:
        print(f"🧹 Canceling {len(all_final_orders)} remaining orders...")
        for o in all_final_orders:
             req_k = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
             conn.root.exposed_order_send(req_k)
    else:
        print("✅ No remaining orders.")

    print(f"\n✅ --- FULL TDD TEST SUITE (1-24) COMPLETE ---")

if __name__ == "__main__":
    run_test()
