# mt5_server.py
import MetaTrader5
from rpyc.utils.server import ThreadedServer
import rpyc

# Define the service that will be exposed to WSL
class MT5Service(rpyc.Service):
    def on_connect(self, conn):
        print("Connected to OpenClaw (WSL)")
    
    def on_disconnect(self, conn):
        print("Disconnected")

    # Expose the MetaTrader5 library methods
    def exposed_get_mt5(self):
        return MetaTrader5
    
    def exposed_order_send(self, request):
        print(f"Received request type: {type(request)}")
        try:
            # Use rpyc generic obtain to get the object by value
            native_request = rpyc.utils.classic.obtain(request)
            print(f"Obtained request: {native_request}")
        except Exception as e:
            print(f"obtain() failed: {e}")
            native_request = {}
                
        print(f"Executing order_send with: {native_request}")
        return MetaTrader5.order_send(native_request)

# Start the server on port 18812
if __name__ == "__main__":
    print("Starting MT5 Bridge Server on Windows...")
    # allow_public_attrs=True is required to access MT5 functions dynamically
    # port 18812 is the default RPyC port, listening on 0.0.0.0 allows connection from WSL
    server = ThreadedServer(MT5Service, port=18812, protocol_config={"allow_public_attrs": True, "allow_pickle": True})
    server.start()