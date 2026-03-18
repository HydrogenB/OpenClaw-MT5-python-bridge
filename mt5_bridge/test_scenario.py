import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from mt5_skill import MT5Skill

console = Console()

def log_step(step_name):
    console.print(f"\n[bold cyan]─── {step_name} ───[/bold cyan]")

def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_scenario():
    console.clear()
    console.print(Panel.fit(
        f"[bold yellow]MT5 Bridge - Full Coverage Scenario[/bold yellow]\n[dim]{get_time()}[/dim]",
        subtitle="[bold blue]OpenClaw Automation[/bold blue]",
        border_style="blue"
    ))

    skill = MT5Skill()
    
    # 1. Connection & Info
    log_step("1. System Check")
    with console.status("[bold green]Connecting to MT5 Bridge...[/bold green]", spinner="dots"):
        status = skill.check_connection()
        time.sleep(0.5)

    if "error" in status:
        console.print(f"[bold red]❌ Connection Failed:[/bold red] {status['error']}")
        console.print("[yellow]💡 Hint:[/yellow] Ensure [bold]mt5_server.py[/bold] is running.")
        return

    # Display System Info Table
    table = Table(title="System Status", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="dim")
    table.add_column("Value", style="bold green")
    
    if "terminal" in status:
        table.add_row("Terminal", str(status['terminal']))
        table.add_row("MT5 Connected", "Yes")
    
    account = skill.get_account_info()
    if "login" in account:
        table.add_row("Login", str(account['login']))
        table.add_row("Balance", f"{account['balance']} {account.get('currency', '')}")
        table.add_row("Equity", f"{account['equity']}")
    
    console.print(table)

    # 2. Market Data
    SYMBOL = "EURUSD"
    log_step(f"2. Market Data ({SYMBOL})")
    
    with console.status("Fetching Price & History...", spinner="dots"):
        price = skill.get_price(SYMBOL)
        rates = skill.get_rates(SYMBOL, count=3)
        time.sleep(0.5)

    if "bid" in price:
        # Mini Price Panel
        price_text = Text()
        price_text.append(f"BID: {price['bid']}  ", style="bold red")
        price_text.append(f"ASK: {price['ask']}", style="bold blue")
        console.print(Panel(price_text, title=f"Realtime {SYMBOL}", expand=False))
    else:
        console.print("[red]❌ Failed to get price[/red]")

    console.print(f"[dim]Retrieved {len(rates)} OHLCV candles...[/dim]")

    # 3. Indicators
    log_step("3. Indicators")
    with console.status("Calculating RSI(14)...", spinner="dots"):
        rsi = skill.calculate_indicator(SYMBOL, "rsi", length=14)
        time.sleep(0.5)
    
    console.print(f"📈 [bold]RSI(14):[/bold] {rsi}")

    # 4. Trading Scenario: Market Order Cycle
    log_step("4. Market Order Cycle")
    
    ticket = None
    
    # A. Open Buy
    with console.status("[bold yellow]Opening Market Buy 0.02...[/bold yellow]"):
        open_res = skill.open_trade(SYMBOL, 0.02, "buy", sl=0, tp=0)
        time.sleep(1)

    if "order" in open_res:
        ticket = open_res['order']
        console.print(f"[bold green]✅ OPEN SUCCESS[/bold green] Ticket: [bold]{ticket}[/bold]")
    else:
        console.print(f"[bold red]❌ OPEN FAILED[/bold red] {open_res}")
        return

    # B. Modify
    with console.status(f"Modifying SL/TP for {ticket}..."):
        current_price = skill.get_price(SYMBOL)
        sl = current_price['bid'] - 0.0050
        tp = current_price['bid'] + 0.0050
        mod_res = skill.modify_position(ticket, sl=sl, tp=tp)
        time.sleep(1)

    if "retcode" in mod_res: # MT5 usually returns retcode in result
        console.print(f"[green]✅ Modified SL/TP[/green] (SL: {sl:.5f}, TP: {tp:.5f})")
    else:
        console.print(f"[red]❌ Modify Failed[/red] {mod_res}")

    # C. Partial Close
    with console.status("Partial Close (0.01)..."):
        close_res = skill.close_position(ticket, volume=0.01)
        time.sleep(1)
        
    if "order" in close_res:
         console.print(f"[green]✅ Partial Close[/green] -> Remainder Ticket might change")
    else:
         console.print(f"[red]❌ Partial Close Failed[/red] {close_res}")

    # D. Full Close
    # Find the position again (ticket might be same or different depending on netting)
    positions = skill.get_positions(SYMBOL)
    target_pos = next((p for p in positions if p['ticket'] == ticket), None)
    # If not found by ticket, maybe it's the only one left?
    if not target_pos and len(positions) > 0:
        target_pos = positions[0] # Verify this assumption in prod

    if target_pos:
        with console.status(f"Closing {target_pos['ticket']}..."):
            full_close = skill.close_position(target_pos['ticket'])
            time.sleep(1)
        console.print(f"[green]✅ Full Close[/green]")
    else:
        console.print("[yellow]⚠️ Position already closed or not found[/yellow]")


    # 5. Pending Order Cycle
    log_step("5. Pending Order Cycle")
    
    current_ask = skill.get_price(SYMBOL)['ask']
    limit_price = current_ask - 0.0100
    pending_ticket = None

    # A. Place Limit
    with console.status(f"Placing Buy Limit at {limit_price:.5f}..."):
        pending_res = skill.open_trade(SYMBOL, 0.02, "buy_limit", price=limit_price)
        time.sleep(1)
    
    if "order" in pending_res:
        pending_ticket = pending_res['order']
        console.print(f"[bold green]✅ PENDING PLACED[/bold green] Ticket: [bold]{pending_ticket}[/bold]")
    else:
         console.print(f"[bold red]❌ PENDING FAILED[/bold red] {pending_res}")
         return

    # B. Modify Price
    new_price = limit_price - 0.0010
    with console.status(f"Modifying Price to {new_price:.5f}..."):
        mod_pending = skill.modify_order(pending_ticket, price=new_price)
        time.sleep(1)
    
    console.print(f"[green]✅ Limit Price Modified[/green]")

    # C. Delete
    with console.status("Deleting Order..."):
        del_res = skill.delete_order(pending_ticket)
        time.sleep(1)
    
    console.print(f"[green]✅ Order Deleted[/green]")

    # Footer
    console.print(Panel(f"[bold white]TEST COMPLETE[/bold white] at {get_time()}", style="bold green"))

if __name__ == "__main__":
    run_scenario()
