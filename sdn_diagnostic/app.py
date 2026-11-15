"""
FastAPI Server connecting the Web UI, UDP Probe Client/Server, Dynamic SDN Flow Manager,
Challenging Scenarios, and Performance Benchmarks (Full Deliverable 1 & 2).
"""
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse

from sdn_diagnostic.probe.server import UDPEchoServer
from sdn_diagnostic.probe.client import UDPProbeClient
from sdn_diagnostic.topology.controller import create_sample_sdn_topology
from sdn_diagnostic.topology.flow_manager import FlowTableManager
from sdn_diagnostic.analysis.correlator import PathCorrelator
from sdn_diagnostic.scenarios.fault_injector import ScenarioManager
from sdn_diagnostic.evaluation.benchmarker import BenchmarkSuite

# Global Core Instances
echo_server = UDPEchoServer(host="127.0.0.1", port=9999)
sdn_topology = create_sample_sdn_topology()
correlator = PathCorrelator(sdn_topology)
flow_manager = FlowTableManager()
scenario_manager = ScenarioManager(sdn_topology, echo_server)
benchmarker = BenchmarkSuite(echo_server)

# Setup initial flow rules matching default active path
flow_manager.install_path_flows(["h1", "s1", "s2", "s4", "h3"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch low-level UDP echo server
    echo_server.start()
    yield
    # Shutdown: Cleanly terminate echo server and scenario threads
    scenario_manager.reset_all()
    echo_server.stop()

app = FastAPI(title="SDN Diagnostic & Dynamic Traffic Manager", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
def get_index():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/topology")
def get_topology():
    topo_data = sdn_topology.serialize()
    topo_data["active_path"] = flow_manager.active_path
    topo_data["flow_tables"] = flow_manager.get_flow_rules()
    topo_data["active_scenario"] = scenario_manager.active_scenario
    return topo_data

@app.get("/api/probe")
def run_probe(
    src: str = Query("h1"),
    dst: str = Query("h3"),
    count: int = Query(10),
    preserve_faults: bool = Query(False)
):
    # Run active UDP socket probe
    client = UDPProbeClient(target_host="127.0.0.1", target_port=9999, timeout=0.8)
    probe_results = client.run_probe(count=count, interval_ms=15.0)

    # Correlate with active SDN topology path
    active_path = flow_manager.active_path
    path_metrics = sdn_topology.get_path_metrics(active_path)
    if not path_metrics.get("is_viable", True):
        probe_results["packet_loss_pct"] = 100.0
        probe_results["avg_rtt_ms"] = 0.0
        probe_results["jitter_ms"] = 0.0

    analysis = correlator.analyze_path_correlation(
        src_host=src,
        dst_host=dst,
        probe_results=probe_results,
        active_path=active_path
    )

    return {
        "probe": probe_results,
        "analysis": analysis,
        "active_path": active_path
    }

# ----------------- Dynamic SDN Functionality (D2: 6 Marks) -----------------

@app.post("/api/sdn/reroute")
def trigger_dynamic_reroute(target_path: list = Body(None)):
    """Dynamically updates OpenFlow flow tables along chosen or optimal backup path."""
    if not target_path:
        # Determine best alternate path automatically
        all_paths = sdn_topology.get_all_paths("h1", "h3")
        viable = [p for p in all_paths if p != flow_manager.active_path and sdn_topology.get_path_metrics(p)["is_viable"]]
        target_path = viable[0] if viable else ["h1", "s1", "s3", "s4", "h3"]

    flow_manager.install_path_flows(target_path)
    # Recover test server impairments if rerouting avoided the degraded link
    if "s2" not in target_path:
        echo_server.artificial_delay_ms = 0.0
        echo_server.artificial_drop_rate = 0.0

    return {
        "status": "reroute_applied",
        "new_active_path": target_path,
        "flow_rules": flow_manager.get_flow_rules()
    }

@app.post("/api/sdn/acl/block")
def block_traffic(host: str = Query("h2")):
    """Installs dynamic OpenFlow ACL drop rule (Priority 500)."""
    res = flow_manager.block_host(host)
    return res

@app.post("/api/sdn/acl/unblock")
def unblock_traffic(host: str = Query("h2")):
    """Removes dynamic OpenFlow ACL drop rule."""
    res = flow_manager.unblock_host(host)
    return res

@app.get("/api/sdn/flows")
def get_flow_tables():
    """Returns all current OpenFlow forwarding and policy rules."""
    return flow_manager.get_flow_rules()

# ----------------- Challenging Scenarios / Robustness (D2: 4 Marks) -----------------

@app.post("/api/scenario/switch-crash")
def run_scenario_switch_crash():
    """Simulates sudden core switch crash on s2."""
    return scenario_manager.run_core_switch_failure("s2")

@app.post("/api/scenario/bufferbloat")
def run_scenario_bufferbloat():
    """Simulates extreme link congestion and queue bloat."""
    return scenario_manager.run_severe_bufferbloat(latency_ms=85.0, loss_pct=35.0)

@app.post("/api/scenario/reset")
def reset_scenario():
    """Restores baseline operating health."""
    global sdn_topology, correlator
    scenario_manager.reset_all()
    flow_manager.unblock_host("h1")
    flow_manager.unblock_host("h2")
    flow_manager.install_path_flows(["h1", "s1", "s2", "s4", "h3"])
    sdn_topology = create_sample_sdn_topology()
    correlator = PathCorrelator(sdn_topology)
    scenario_manager.topology = sdn_topology
    return {"status": "baseline_reset_complete"}

# Backwards compatible endpoints
@app.post("/api/fault/degrade")
def inject_degradation():
    return scenario_manager.run_severe_bufferbloat(latency_ms=40.0, loss_pct=25.0)

@app.post("/api/fault/break")
def inject_link_break():
    return scenario_manager.run_core_switch_failure("s2")

@app.post("/api/fault/reset")
def reset_faults():
    return reset_scenario()

def main():
    uvicorn.run("sdn_diagnostic.app:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
