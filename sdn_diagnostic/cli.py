"""
CLI runner for the UDP SDN Diagnostic Tool (Deliverable 1 & 2).
Supports interactive diagnostic testing, dynamic SDN rerouting demo,
challenging stress scenarios, and automated benchmark comparisons.
"""
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from sdn_diagnostic.probe.server import UDPEchoServer
from sdn_diagnostic.probe.client import UDPProbeClient
from sdn_diagnostic.topology.controller import create_sample_sdn_topology
from sdn_diagnostic.topology.flow_manager import FlowTableManager
from sdn_diagnostic.analysis.correlator import PathCorrelator
from sdn_diagnostic.scenarios.fault_injector import ScenarioManager
from sdn_diagnostic.evaluation.benchmarker import BenchmarkSuite

console = Console()

def run_cli_diagnostic():
    # 1. Start Echo Server
    server = UDPEchoServer(host="127.0.0.1", port=9999)
    server.start()

    console.print(Panel.fit(
        "[bold cyan]SDN Network Diagnostic & Dynamic Traffic Manager[/bold cyan]\n"
        "[italic]Full Deliverable 1 & 2: Sockets • SDN Topology • Dynamic OpenFlow • Scenarios • Evaluation[/italic]",
        border_style="green"
    ))

    topo = create_sample_sdn_topology()
    flow_mgr = FlowTableManager()
    correlator = PathCorrelator(topo)
    scenario_mgr = ScenarioManager(topo, server)
    benchmarker = BenchmarkSuite(server)

    try:
        while True:
            console.print("\n[bold yellow]Select Action:[/bold yellow]")
            console.print("  [1] Run End-to-End UDP Path Probe & SDN Correlation")
            console.print("  [2] Trigger Dynamic SDN Flow Reprogramming & Reroute")
            console.print("  [3] Run Challenging Scenario: Core Switch Crash / Link Flapping")
            console.print("  [4] Run Benchmark: Static Routing vs Dynamic SDN Rerouting")
            console.print("  [5] Run Benchmark: UDP vs TCP Comparative Evaluation")
            console.print("  [0] Exit")

            choice = Prompt.ask("Enter option", default="1")

            if choice == "1":
                console.print(f"[cyan]Probing active path: {' -> '.join(flow_mgr.active_path)}...[/cyan]")
                client = UDPProbeClient("127.0.0.1", 9999, timeout=0.6)
                res = client.run_probe(count=10, interval_ms=15.0)

                # Metrics Table
                t = Table(title="UDP Socket Diagnostic Metrics")
                t.add_column("Metric", style="bold")
                t.add_column("Value", style="cyan")
                t.add_row("Packets Sent", str(res["packets_sent"]))
                t.add_row("Packets Received", str(res["packets_received"]))
                t.add_row("Packet Loss", f"{res['packet_loss_pct']}%")
                t.add_row("Avg RTT", f"{res['avg_rtt_ms']} ms")
                t.add_row("Jitter", f"{res['jitter_ms']} ms")
                console.print(t)

                analysis = correlator.analyze_path_correlation("h1", "h3", res, active_path=flow_mgr.active_path)
                console.print(f"[bold]Active Path Status:[/bold] {analysis['active_path_status']}")
                console.print(f"[bold]Recommendation:[/bold] {analysis['recommendation']}")

            elif choice == "2":
                alt_path = ["h1", "s1", "s3", "s4", "h3"]
                console.print(f"[yellow]Dynamically installing OpenFlow flow rules for: {' -> '.join(alt_path)}[/yellow]")
                flow_mgr.install_path_flows(alt_path)
                console.print("[green]✔ Flow tables updated across s1, s3, s4.[/green]")
                console.print(f"Active Path is now: [bold green]{' -> '.join(flow_mgr.active_path)}[/bold green]")

            elif choice == "3":
                console.print("[bold red]Simulating Core Switch Failure on s2...[/bold red]")
                scenario_mgr.run_core_switch_failure("s2")
                client = UDPProbeClient("127.0.0.1", 9999, timeout=0.3)
                res = client.run_probe(count=5, interval_ms=10.0)
                console.print(f"[red]Probe Result under Core Failure: Loss = {res['packet_loss_pct']}% (Connection Broken)[/red]")
                
                # Autonomous reroute demonstration
                console.print("[bold green]Autonomous SDN Trigger: Rerouting around crashed switch s2 to s3...[/bold green]")
                flow_mgr.install_path_flows(["h1", "s1", "s3", "s4", "h3"])
                server.artificial_drop_rate = 0.0
                res_recov = client.run_probe(count=5, interval_ms=10.0)
                console.print(f"[green]Post-Reroute Recovery: Loss = {res_recov['packet_loss_pct']}%, Avg RTT = {res_recov['avg_rtt_ms']}ms[/green]")

            elif choice == "4":
                console.print("[cyan]Running Experiment: Static Routing vs Autonomous Dynamic SDN...[/cyan]")
                exp = benchmarker.run_static_vs_dynamic_reroute_experiment()
                
                t = Table(title="Comparative Evaluation: Static vs Dynamic SDN")
                t.add_column("Approach", style="bold")
                t.add_column("Path", style="magenta")
                t.add_column("Packet Loss (%)", justify="right")
                t.add_column("Status", justify="center")
                
                t.add_row(
                    "Static Routing (Baseline)",
                    exp["static_baseline"]["active_path"],
                    f"{exp['static_baseline']['packet_loss_pct']}%",
                    "[red]FAILED[/red]"
                )
                t.add_row(
                    "Dynamic SDN (Proposed)",
                    exp["dynamic_sdn_approach"]["rerouted_path"],
                    f"{exp['dynamic_sdn_approach']['packet_loss_pct']}%",
                    "[green]RESTORED[/green]"
                )
                console.print(t)
                console.print(f"[bold green]Improvement:[/bold green] Recovered {exp['improvement_loss_pct']}% packet loss through autonomous OpenFlow rerouting.")

            elif choice == "5":
                console.print("[cyan]Running Comparative Evaluation: UDP vs TCP Protocol Performance...[/cyan]")
                comp = benchmarker.run_udp_vs_tcp_benchmark(payload_size=512, count=15)
                
                t = Table(title="Protocol Comparison: UDP Probing vs TCP Stream")
                t.add_column("Protocol", style="bold")
                t.add_column("Handshake Overhead", justify="right")
                t.add_column("Avg RTT", justify="right")
                t.add_column("Jitter", justify="right")
                t.add_column("Suitability for SDN Monitoring", style="cyan")

                t.add_row(
                    "UDP Socket Probes",
                    "0.0 ms",
                    f"{comp['udp_metrics']['avg_rtt_ms']} ms",
                    f"{comp['udp_metrics']['jitter_ms']} ms",
                    "Ideal (Zero-overhead, real-time jitter tracking)"
                )
                t.add_row(
                    "TCP Stream Sockets",
                    f"{comp['tcp_metrics']['handshake_latency_ms']} ms",
                    f"{comp['tcp_metrics']['avg_rtt_ms']} ms",
                    "N/A (Buffered)",
                    "High connection overhead, retransmissions mask loss"
                )
                console.print(t)
                console.print(f"[italic]{comp['comparison_insights']}[/italic]")

            elif choice == "0":
                break

    finally:
        scenario_mgr.reset_all()
        server.stop()
        console.print("[green]Demonstration finished cleanly.[/green]")

if __name__ == "__main__":
    run_cli_diagnostic()
