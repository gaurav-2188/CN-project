"""
CLI runner for the UDP SDN Diagnostic Tool.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from sdn_diagnostic.probe.server import UDPEchoServer
from sdn_diagnostic.probe.client import UDPProbeClient
from sdn_diagnostic.topology.controller import create_sample_sdn_topology
from sdn_diagnostic.analysis.correlator import PathCorrelator

console = Console()

def run_cli_diagnostic():
    # 1. Start Echo Server
    server = UDPEchoServer(host="127.0.0.1", port=9999)
    server.start()

    console.print(Panel.fit("[bold green]SDN Network Diagnostic & Path Analysis Tool[/bold green]", subtitle="UDP Probing & Topology Correlation"))

    # 2. Setup Topology & Correlator
    topo = create_sample_sdn_topology()
    correlator = PathCorrelator(topo)

    # 3. Perform UDP Probe
    console.print("[cyan]Sending 10 UDP probe packets to destination...[/cyan]")
    client = UDPProbeClient("127.0.0.1", 9999)
    probe_results = client.run_probe(count=10, interval_ms=20.0)

    # 4. Display Probe Metrics
    metrics_table = Table(title="UDP Diagnostic Probe Metrics")
    metrics_table.add_column("Metric", style="bold")
    metrics_table.add_column("Value", style="cyan")

    metrics_table.add_row("Packets Sent", str(probe_results["packets_sent"]))
    metrics_table.add_row("Packets Received", str(probe_results["packets_received"]))
    metrics_table.add_row("Packet Loss", f"{probe_results['packet_loss_pct']}%")
    metrics_table.add_row("Avg RTT", f"{probe_results['avg_rtt_ms']} ms")
    metrics_table.add_row("Min / Max RTT", f"{probe_results['min_rtt_ms']} ms / {probe_results['max_rtt_ms']} ms")
    metrics_table.add_row("Jitter", f"{probe_results['jitter_ms']} ms")
    console.print(metrics_table)

    # 5. Correlate with SDN Topology
    analysis = correlator.analyze_path_correlation(
        src_host="h1",
        dst_host="h3",
        probe_results=probe_results
    )

    console.print(f"\n[bold]Active Path:[/bold] {' -> '.join(analysis['active_path'])} [{analysis['active_path_status']}]")
    console.print(f"[bold]Recommendation:[/bold] {analysis['recommendation']}")

    # 6. Alternate Paths Table
    alt_table = Table(title="SDN Alternative Paths Evaluation")
    alt_table.add_column("Path", style="magenta")
    alt_table.add_column("Hops", justify="center")
    alt_table.add_column("Expected Delay", justify="right")
    alt_table.add_column("Status", justify="center")

    for p in analysis["alternative_paths"]:
        path_str = " -> ".join(p["path"])
        status = "[green]HEALTHY[/green]" if p["is_viable"] else "[red]FAILED[/red]"
        alt_table.add_row(path_str, str(p["hop_count"]), f"{p['expected_delay_ms']} ms", status)
    
    console.print(alt_table)

    server.stop()

if __name__ == "__main__":
    run_cli_diagnostic()
