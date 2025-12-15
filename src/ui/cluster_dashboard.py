import asyncio
from datetime import datetime
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.console import Console
from rich.text import Text
from src.core.node import Node
console = Console()

def node_panel(node):
    """Render a panel for one node."""

    # If dead — show red offline panel
    if not node.is_alive:
        return Panel(
            Text(f"Node {node.node_id} OFFLINE", style="bold red"),
            border_style="red",
            title=f"[red]Node {node.node_id}",
        )
    # Role Display
    role_style = "bold green" if node.role == "leader" else "bold cyan"
    role_text = Text(node.role.upper(), style=role_style)

    # Sensor Table
    sensor_table = Table(show_header=True, header_style="bold magenta", expand=True)
    sensor_table.add_column("Node")
    sensor_table.add_column("Value")

    for nid, sv in sorted(node.state.state.items()):
        if sv.value is not None:
            sensor_table.add_row(nid, f"{sv.value:.2f}")

    # Election Information
    election_info = Text()
    if node.role == "candidate":
        election_info.append(f"Election ongoing\n", style="yellow")
        election_info.append(f"Votes: {len(node.votes_received)}\n", style="yellow")

    panel = Panel(
        sensor_table,
        title=f"Node {node.node_id}",
        subtitle=f"Role: {role_text.plain} | Term: {node.term}",
        border_style="bright_blue" if node.role != "leader" else "green",
    )
    return panel


def build_layout(nodes):
    layout = Layout()

    # Header
    header = Text(
        f"Distributed Sensor Fusion Cluster — {datetime.now().strftime('%H:%M:%S')}",
        style="bold white on dark_green",
        justify="center",
    )

    layout.split_column(
        Layout(header, name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="events", size=15),
    )

    # Body has 3 node panels
    layout["body"].split_row(
        Layout(node_panel(nodes[0]), name="A"),
        Layout(node_panel(nodes[1]), name="B"),
        Layout(node_panel(nodes[2]), name="C"),
    )

    # Event log window
    event_text = Text()
    for node in nodes:
        for line in node.events[-8:]:
            event_text.append(line + "\n", style="white")

    layout["events"].update(Panel(event_text, title="Cluster Events", border_style="blue"))

    return layout


async def input_handler(nodes):
    """Handle dashboard keyboard input."""
    while True:
        key = await asyncio.to_thread(console.input, "")
        key = key.strip()

        if key == "1":
            nodes[0].stop()
        elif key == "2":
            nodes[1].stop()
        elif key == "3":
            nodes[2].stop()
        elif key == "q":
            for n in nodes:
                n.stop()
            return


async def run_cluster_dashboard(nodes):
    asyncio.create_task(input_handler(nodes))

    with Live(refresh_per_second=4, screen=True) as live:
        while True:
            live.update(build_layout(nodes))
            await asyncio.sleep(0.25)
