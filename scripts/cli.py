"""How setup, doctor and uninstall print: a rule per section and aligned rows with a coloured status word."""
from rich.console import Console
from rich.table import Table

console = Console(highlight=False, soft_wrap=False)
if not console.is_terminal:
    console.width = 200
STYLE = {"ok": "green", "MISSING": "bold red", "optional": "yellow", "set": "cyan", "found": "green", "asked": "cyan",
         "later": "yellow", "added": "green", "kept": "green", "removed": "green", "made": "green", "failed": "bold red", "done": "green"}


def section(title: str) -> None:
    console.print()
    console.rule(f"[bold cyan]{title}", align="left", style="cyan")


def rows(items: list[tuple[str, str, str]]) -> None:
    """(status, name, detail) rows: the status word coloured, name and detail aligned in columns."""
    t = Table(show_header=False, box=None, padding=(0, 2, 0, 0), pad_edge=False)
    t.add_column(no_wrap=True)
    t.add_column(no_wrap=True, style="bold")
    t.add_column(overflow="fold")
    for status, name, detail in items:
        t.add_row(f"[{STYLE.get(status, 'white')}]{status}[/]", name, detail)
    console.print(t)


def say(text: str, style: str = "") -> None:
    console.print(text, style=style)
