#!/usr/bin/env python3
import argparse
import os
import mmap
import shutil
import random
import string
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.panel import Panel

console = Console()

STRINGS_TO_REPLACE = ["do relocation protocol version", "yielding the value", "msvcrt"]

PRINTABLE_BYTES = (string.ascii_letters).encode()

RESULT_DIR = "result"
DEPENDENCIES_DIR = "dependencies"

def random_bytes(length: int) -> bytes:
    return bytes(random.choice(PRINTABLE_BYTES) for _ in range(length))

def find_and_replace_inplace(path: str, targets: list[str]):
    replaced = []
    with open(path, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        try:
            for s in track(targets, description="[cyan]Scanning strings...[/cyan]"):
                target = s.encode()
                pos = mm.find(target, 0)
                while pos != -1:
                    repl = random_bytes(len(target))
                    mm[pos:pos+len(target)] = repl
                    replaced.append((s, repl, pos))
                    pos = mm.find(target, pos + len(target))
            mm.flush()
        finally:
            mm.close()
    return replaced

def main():
    parser = argparse.ArgumentParser(description="Replace predefined strings in a binary file with random bytes of equal length (only on a copy).")
    parser.add_argument("-f", "--file", required=True, help="Path to the target file")
    args = parser.parse_args()

    console.rule("[bold green]Adaptix Obfuscator[/bold green]")

    src = args.file
    if not os.path.isfile(src):
        console.print(f"[red]File not found:[/red] {src}")
        return

    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)

    base_name = os.path.basename(src)
    result_binary_path = os.path.join(RESULT_DIR, base_name)
    shutil.copy2(src, result_binary_path)
    console.print(f"[cyan]Copied original binary to:[/cyan] {result_binary_path}")

    replacements = find_and_replace_inplace(result_binary_path, STRINGS_TO_REPLACE)

    if not replacements:
        console.print("[bold red]No matches found.[/bold red]")
        return

    table = Table(title="Replacements Summary", show_lines=True, header_style="bold magenta")
    table.add_column("Original", style="bold cyan")
    table.add_column("Replacement (printable)", style="green")
    table.add_column("Offset", style="yellow")

    msvcrt_replacement = None

    for orig, repl, pos in replacements:
        try:
            printable = ''.join(c if c.isprintable() else '.' for c in repl.decode('utf-8'))
        except Exception:
            printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in repl)
        table.add_row(orig, printable, f"{pos} (0x{pos:X})")
        if orig.lower() == "msvcrt":
            msvcrt_replacement = printable

    console.print(Panel("[bold green]Replacements completed successfully![/bold green]", expand=False))
    console.print(table)

    if msvcrt_replacement:
        msvcrt_source = os.path.join(DEPENDENCIES_DIR, "msvcrt.dll")
        if os.path.isfile(msvcrt_source):
            safe_name = "".join(c if c.isalnum() else "_" for c in msvcrt_replacement)
            msvcrt_dest = os.path.join(RESULT_DIR, f"{safe_name}.dll")
            shutil.copy2(msvcrt_source, msvcrt_dest)
            console.print(f"[cyan]Copied and renamed msvcrt.dll to:[/cyan] {msvcrt_dest}")
        else:
            console.print(f"[yellow]msvcrt.dll not found in dependencies folder[/yellow]")

    console.rule("[bold green]Done[/bold green]")

if __name__ == "__main__":
    main()