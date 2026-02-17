# mt5_server.py
import MetaTrader5
import rpyc
from rpyc.utils.server import ThreadedServer
import threading
import time
from datetime import datetime
from collections import deque
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

# --- Server State for TUI ---
class ServerState:
    def __init__(self):
        self.logs = deque(maxlen=20)
        self.connections = 0
        self.requests_total = 0
        self.errors_total = 0
        self.mt5_connected = False
        self.mt5_login = "N/A"
        self.server_start_time = datetime.now()
        self.last_update = datetime.now()

    def log(self, message, status="INFO"):
        self.logs.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "status": status
        })

state = ServerState()

# --- MT5 Service ---
class MT5Service(rpyc.Service):
    def on_connect(self, conn):
        state.connections += 1
        state.log(f"New Connection: {conn}", "INFO")
    
    def on_disconnect(self, conn):
        state.connections = max(0, state.connections - 1)
        state.log(f"Disconnected: {conn}", "WARN")

    def exposed_get_mt5(self):
        # Expose the MetaTrader5 library methods
        return MetaTrader5
    
    def exposed_order_send(self, request):
        state.requests_total += 1
        start = time.time()
        try:
            # Use rpyc generic obtain to get the object by value
            native_request = rpyc.utils.classic.obtain(request)
            state.log(f"Order Request: {native_request}", "REQ")
            
            result = MetaTrader5.order_send(native_request)
            
            duration = (time.time() - start) * 1000
            status = "OK" if result.retcode == MetaTrader5.TRADE_RETCODE_DONE else "FAIL"
            state.log(f"Order Result: retcode={result.retcode} ({duration:.1f}ms)", status)
            
            if status == "FAIL": state.errors_total += 1
            return result
            
        except Exception as e:
            state.errors_total += 1
            state.log(f"Error processing order: {e}", "ERR")
            return None

# --- TUI Components ---

def make_layout() -> Layout:
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="logs", ratio=2),
        Layout(name="stats", ratio=1),
    )
    return layout

def render_header():
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right")
    grid.add_row(
        Text("MT5 RPyC Bridge Server", style="bold white"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    return Panel(grid, style="white on blue")

def render_stats():
    table = Table(box=ROUNDED, expand=True)
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right", style="bold")
    
    status_style = "green" if state.mt5_connected else "red"
    status_text = "CONNECTED" if state.mt5_connected else "DISCONNECTED"
    
    table.add_row("MT5 Status", f"[{status_style}]{status_text}[/{status_style}]")
    if state.mt5_login != "N/A":
        table.add_row("Login", str(state.mt5_login))
    
    table.add_row("Active Connections", str(state.connections))
    table.add_row("Total Requests", str(state.requests_total))
    table.add_row("Errors", f"[red]{state.errors_total}[/red]" if state.errors_total > 0 else "0")
    
    uptime = datetime.now() - state.server_start_time
    table.add_row("Uptime", str(uptime).split('.')[0])
    
    return Panel(table, title="Server Stats", border_style="blue")

def render_logs():
    table = Table(box=None, expand=True, show_header=False)
    table.add_column("Time", width=10, style="dim")
    table.add_column("Status", width=6)
    table.add_column("Message")
    
    for log in list(state.logs):
        color = "green"
        if log['status'] in ["WARN", "FAIL"]: color = "yellow"
        if log['status'] == "ERR": color = "red"
        if log['status'] == "REQ": color = "cyan"
        
        table.add_row(
            log['time'],
            f"[{color}]{log['status']}[/{color}]",
            str(log['message'])
        )
        
    return Panel(table, title="Event Log", border_style="white")

def run_tui(event_stop):
    console = Console()
    layout = make_layout()
    
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while not event_stop.is_set():
            layout["header"].update(render_header())
            layout["logs"].update(render_logs())
            layout["stats"].update(render_stats())
            layout["footer"].update(Panel(f"Listening on [bold]0.0.0.0:18812[/bold] (RPyC). Press Ctrl+C to stop.", style="dim"))
            time.sleep(0.25)

# --- Main Entry Point ---
if __name__ == "__main__":
    # Initialize MT5
    if not MetaTrader5.initialize():
        state.log(f"MT5 Init Failed: {MetaTrader5.last_error()}", "ERR")
    else:
        state.mt5_connected = True
        info = MetaTrader5.account_info()
        if info:
            state.mt5_login = info.login
            state.log(f"MT5 Initialized. Login: {info.login}", "INFO")

    # Start RPyC Server in a Thread
    server = ThreadedServer(MT5Service, port=18812, protocol_config={"allow_public_attrs": True, "allow_pickle": True})
    t_server = threading.Thread(target=server.start)
    t_server.daemon = True # Allow exit when main thread exits
    t_server.start()
    
    stop_event = threading.Event()
    try:
        run_tui(stop_event)
    except KeyboardInterrupt:
        stop_event.set()
        # RPyC server.close() isn't clean always, but daemon thread helps
        server.close()
        MetaTrader5.shutdown()
        print("Server Stopped")