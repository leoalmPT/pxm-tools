
from rich.console import Console

def main():
    console = Console()
    console.print("Proxmox CLI Tools", style="bold cyan")
    console.print("=" * 20, style="bold")
    console.print("This is a set of tools to manage Proxmox VMs from the command line.")
    console.print("The tools are:")
    console.print("[bold green] - pxm-create:[/bold green] Create VMs from a template")
    console.print("[bold green] - pxm-edit:[/bold green] Edit VMs")
    console.print("[bold green] - pxm-rm:[/bold green] Remove VMs")
    console.print("[bold green] - pxm-start:[/bold green] Start VMs and get their IP addresses")
    console.print("[bold green] - pxm-stop:[/bold green] Stop VMs")
