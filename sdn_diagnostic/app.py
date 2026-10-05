"""
FastAPI Server connecting the Web UI, UDP Probe Client/Server, and SDN Correlator.
Provides simple 1-click REST endpoints.
"""
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import uvicorn

from sdn_diagnostic.probe.server import UDPEchoServer
from sdn_diagnostic.probe.client import UDPProbeClient
from sdn_diagnostic.topology.controller import create_sample_sdn_topology
from sdn_diagnostic.analysis.correlator import PathCorrelator

app = FastAPI(title="SDN Diagnostic Tool")

# Global instances
echo_server = UDPEchoServer(host="127.0.0.1", port=9999)
sdn_topology = create_sample_sdn_topology()
correlator = PathCorrelator(sdn_topology)

# Start echo server automatically
@app.on_event("startup")
def startup_event():
    echo_server.start()

@app.on_event("shutdown")
def shutdown_event():
    echo_server.stop()

@app.get("/", response_class=HTMLResponse)
def get_index():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/topology")
def get_topology():
    return sdn_topology.serialize()

@app.get("/api/probe")
def run_probe(
    src: str = Query("h1"),
    dst: str = Query("h3"),
    count: int = Query(10),
    preserve_faults: bool = Query(False)
):
    # If not preserving injected test faults, ensure clean baseline
    if not preserve_faults and echo_server.artificial_delay_ms == 0 and echo_server.artificial_drop_rate == 0:
        pass

    # Run active UDP socket probe
    client = UDPProbeClient(target_host="127.0.0.1", target_port=9999, timeout=0.8)
    probe_results = client.run_probe(count=count, interval_ms=15.0)

    # Correlate with SDN topology paths
    all_paths = sdn_topology.get_all_paths(src, dst)
    active_path = all_paths[0] if all_paths else []
    
    analysis = correlator.analyze_path_correlation(
        src_host=src,
        dst_host=dst,
        probe_results=probe_results,
        active_path=active_path
    )

    return {
        "probe": probe_results,
        "analysis": analysis
    }

@app.post("/api/fault/degrade")
def inject_degradation():
    """Simulates 40ms extra delay and 25% packet drop on active link s1-s2."""
    echo_server.artificial_delay_ms = 40.0
    echo_server.artificial_drop_rate = 0.25
    # Mark in topology
    for link_id in sdn_topology.link_stats:
        if ("s1" in link_id and "s2" in link_id):
            sdn_topology.set_link_status(link_id, delay_ms=45.0, loss_pct=25.0)
    return {"status": "degradation_injected", "delay_ms": 40.0, "drop_rate": 0.25}

@app.post("/api/fault/break")
def inject_link_break():
    """Simulates complete link failure on s2-s4 (100% drop)."""
    echo_server.artificial_drop_rate = 1.0
    for link_id in sdn_topology.link_stats:
        if ("s2" in link_id and "s4" in link_id):
            sdn_topology.set_link_status(link_id, is_failed=True, loss_pct=100.0)
    return {"status": "link_broken", "link": "s2-s4"}

@app.post("/api/fault/reset")
def reset_faults():
    """Restores baseline conditions."""
    global sdn_topology, correlator
    echo_server.artificial_delay_ms = 0.0
    echo_server.artificial_drop_rate = 0.0
    sdn_topology = create_sample_sdn_topology()
    correlator = PathCorrelator(sdn_topology)
    return {"status": "reset_successful"}

def main():
    uvicorn.run("sdn_diagnostic.app:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
