#!/usr/bin/env python3
"""
MT5 RPyC Server - FIXED VERSION (Limit Order Support)
Run this on Windows where MT5 is installed

This version safely unboxes RPyC Netref dictionaries and forcibly
casts all numerical and string values to their native Python types
(int, float, str). This prevents `mt5.order_send` returning `None`
when passing Numpy-types or RPyC proxy objects.
"""
import MetaTrader5 as mt5
from rpyc.utils.server import ThreadedServer
import rpyc

class MT5Service(rpyc.Service):
    """RPyC Service for MT5 - Fixed for order execution"""
    
    ALIASES = ["mt5"]
    
    def on_connect(self, conn):
        if not mt5.initialize():
            print(f"⚠️ MT5 initialize failed: {mt5.last_error()}")
    
    def on_disconnect(self, conn):
        mt5.shutdown()
    
    def exposed_get_mt5(self):
        return mt5
    
    def exposed_get_account_info(self):
        info = mt5.account_info()
        if info is None:
            return None
        return {
            'login': info.login,
            'balance': info.balance,
            'equity': info.equity,
            'profit': info.profit,
            'margin': info.margin,
            'margin_free': info.margin_free,
            'leverage': info.leverage,
            'currency': info.currency,
            'server': info.server,
            'company': info.company,
            'trade_allowed': info.trade_allowed
        }
    
    def exposed_get_positions(self):
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [
            {
                'ticket': p.ticket,
                'symbol': p.symbol,
                'type': p.type,
                'volume': p.volume,
                'price_open': p.price_open,
                'price_current': p.price_current,
                'sl': p.sl,
                'tp': p.tp,
                'profit': p.profit,
                'swap': p.swap,
                'comment': p.comment,
                'time': p.time
            }
            for p in positions
        ]
    
    def exposed_get_tick(self, symbol):
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'spread': tick.ask - tick.bid,
            'time': tick.time
        }
    
    def exposed_order_send(self, request):
        """KEY FIX: Unbox Netref locally, enforce native types, return as dict"""
        print(f"[SERVER] order_send received proxy: {request}")
        
        # 1. MT5 C-API requires a PURE dictionary, not an RPyC Netref string/dict representation
        # 2. MT5 C-API requires native Python types (int, float, str), NOT numpy.float64 or numpy.int64
        # We manually build a pure local dictionary out of the RPyC Netref object
        
        FLOAT_FIELDS = ['volume', 'price', 'stoplimit', 'sl', 'tp', 'deviation']
        INT_FIELDS = ['action', 'magic', 'order', 'type', 'type_time', 'type_filling', 'position', 'position_by', 'expiration']
        STRING_FIELDS = ['symbol', 'comment']
        
        native_request = {}
        try:
            # Safely iterate through the RPyC Netref Dictionary
            keys = list(request.keys())
            for k in keys:
                v = request[k]
                if v is None:
                    continue
                # Cast to strictly native python primitive types to satisfy MT5 python module
                if k in FLOAT_FIELDS:
                    native_request[k] = float(v)
                elif k in INT_FIELDS:
                    native_request[k] = int(v)
                elif k in STRING_FIELDS:
                    native_request[k] = str(v)
                else:
                    native_request[k] = v
        except Exception as e:
            return {
                'success': False,
                'retcode': -1,
                'comment': f'Failed to unbox Netref dict. Error: {str(e)}',
                'order': 0, 'volume': 0, 'price': 0
            }
            
        print(f"[SERVER] Extracted Native dict: {native_request}")
        
        result = mt5.order_send(native_request)
        print(f"[SERVER] Native MT5 result: {result}")
        
        if result is None:
            error = mt5.last_error()
            return {
                'success': False,
                'retcode': -1,
                'comment': f'MT5 returned None (Invalid Params). Error: {error}',
                'order': 0,
                'volume': 0,
                'price': 0
            }
        
        return {
            'success': result.retcode == 10009,
            'retcode': result.retcode,
            'comment': result.comment or '',
            'order': result.order or 0,
            'volume': result.volume or 0,
            'price': result.price or 0
        }
    def exposed_order_send_json(self, request_json):
        """Accept JSON string, convert to native dict, execute order"""
        import json
        
        print(f"[SERVER] order_send_json received")
        
        try:
            # Parse JSON to native Python dict
            request = json.loads(request_json)
            print(f"[SERVER] Parsed request: {request}")
        except Exception as e:
            return {
                'success': False,
                'retcode': -1,
                'comment': f'JSON parse error: {str(e)}',
                'order': 0, 'volume': 0, 'price': 0
            }
        
        # Build native request with proper types
        FLOAT_FIELDS = ['volume', 'price', 'stoplimit', 'sl', 'tp', 'deviation']
        INT_FIELDS = ['action', 'magic', 'order', 'type', 'type_time', 'type_filling', 'position', 'position_by', 'expiration']
        STRING_FIELDS = ['symbol', 'comment']
        
        native_request = {}
        for k, v in request.items():
            if v is None:
                continue
            if k in FLOAT_FIELDS:
                native_request[k] = float(v)
            elif k in INT_FIELDS:
                native_request[k] = int(v)
            elif k in STRING_FIELDS:
                native_request[k] = str(v)
            else:
                native_request[k] = v
        
        print(f"[SERVER] Native dict: {native_request}")
        
        result = mt5.order_send(native_request)
        print(f"[SERVER] MT5 result: {result}")
        
        if result is None:
            error = mt5.last_error()
            return {
                'success': False,
                'retcode': -1,
                'comment': f'MT5 returned None. Error: {error}',
                'order': 0, 'volume': 0, 'price': 0
            }
        
        return {
            'success': result.retcode == 10009,
            'retcode': result.retcode,
            'comment': result.comment or '',
            'order': result.order or 0,
            'volume': result.volume or 0,
            'price': result.price or 0
        }
    
    def exposed_order_delete(self, ticket):
        request = {
            'action': mt5.TRADE_ACTION_REMOVE,
            'order': ticket
        }
        return self.exposed_order_send(request)
    
    def exposed_position_close(self, ticket, volume=None):
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {'success': False, 'comment': f'Position #{ticket} not found'}
        
        pos = position[0]
        close_volume = volume or pos.volume
        tick = mt5.symbol_info_tick(pos.symbol)
        
        if pos.type == 0:  # BUY
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:  # SELL
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'position': int(ticket),
            'symbol': str(pos.symbol),
            'volume': float(close_volume),
            'type': int(order_type),
            'price': float(price),
            'deviation': 10,
            'comment': 'Adam Smith Close',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC
        }
        return self.exposed_order_send(request)

def main():
    print("=" * 50)
    print("  MT5 RPyC Server (FIXED WITH NATIVE TYPES)")
    print("=" * 50)
    
    if not mt5.initialize():
        print(f"❌ MT5 init failed: {mt5.last_error()}")
        return
    
    account = mt5.account_info()
    if account:
        print(f"✅ MT5: {account.login} @ {account.server}")
        print(f"   Balance: ${account.balance:.2f} | Equity: ${account.equity:.2f}")
    
    print(f"\n🚀 Server on port 18812...\n")
    
    server = ThreadedServer(
        MT5Service,
        port=18812,
        protocol_config={'allow_pickle': True, 'allow_public_attrs': True}
    )
    server.start()

if __name__ == "__main__":
    main()
