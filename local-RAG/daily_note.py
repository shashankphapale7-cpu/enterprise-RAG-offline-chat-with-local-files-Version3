"""
AI Memory OS — Daily Note Quick Capture (Enterprise Edition)
Supports multi-tenant username scoping and auto-ingestion.
"""

import datetime
from pathlib import Path
from rich.console import Console
from auth import get_user_data_dir, authenticate

DATA_DIR = Path(__file__).parent / "data"
console = Console()


def add_daily_note():
    console.print(f"[bold cyan]📝 Daily Note Quick Capture[/bold cyan]")

    username = console.input("[bold yellow]Enter your username: [/bold yellow]").strip()
    if not username:
        console.print("[red]Username required.[/red]")
        return

    password = console.input("[bold yellow]Enter password: [/bold yellow]", password=True).strip()
    if not authenticate(username, password):
        console.print("[red]❌ Authentication failed.[/red]")
        return

    user_data_dir = get_user_data_dir(username)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.date.today().strftime("%Y-%m-%d")
    note_file = user_data_dir / f"{today}.txt"

    console.print(f"[green]✓ Authenticated as {username}[/green]")
    console.print(f"[dim]Enter your note below (empty line to finish):[/dim]\n")

    lines = []
    while True:
        try:
            line = input("> ")
            if not line.strip() and len(lines) > 0:
                break
            lines.append(line)
        except EOFError:
            break

    content = "\n".join(lines).strip()
    if not content:
        console.print("[yellow]Empty note. Nothing saved.[/yellow]")
        return

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_entry = f"\n--- [{timestamp}] ---\n{content}\n"

    with open(note_file, "a", encoding="utf-8") as f:
        f.write(formatted_entry)

    console.print(f"[bold green]✓ Note appended to {note_file.name}![/bold green]")

    # Auto-ingest note into user's ChromaDB vault
    console.print("[cyan]Indexing note into memory...[/cyan]")
    from ingest import ingest
    stats = ingest(data_dir=user_data_dir, show_progress=False, tenant_id=username)
    console.print(f"[bold green]✓ Memory updated! ({stats['chunks_created']} total chunks indexed)[/bold green]")


if __name__ == "__main__":
    add_daily_note()
