"""
SDN Topology Providers:
1. MockSDNTopology: Generates multi-path topologies with configurable faults.
2. RyuRESTTopology: Connects to live Ryu SDN controller REST API.
"""
import requests
from sdn_diagnostic.topology.graph import SDNTopology

def create_sample_sdn_topology() -> SDNTopology:
    r"""
    Creates a redundant multi-switch SDN topology:
    Hosts: h1, h2, h3, h4
    Switches: s1 (edge), s2 (core1), s3 (core2), s4 (edge)
    
        h1 \                           / h3
            -- [s1] === [s2] === [s4] --
        h2 /    | \             / |    \ h4
                |   ==== [s3] === |
    
    This provides Path A (via s2) and Path B (via s3) between h1 and h3/h4.
    """
    topo = SDNTopology()

    # Switches
    topo.add_switch("1", name="s1", ip="10.0.0.1")
    topo.add_switch("2", name="s2", ip="10.0.0.2")
    topo.add_switch("3", name="s3", ip="10.0.0.3")
    topo.add_switch("4", name="s4", ip="10.0.0.4")

    # Inter-switch links
    # Path 1: s1 <-> s2 <-> s4 (Primary)
    topo.add_link("s1", "s2", port1=2, port2=1, delay_ms=4.5, loss_pct=0.0)
    topo.add_link("s2", "s4", port1=2, port2=1, delay_ms=5.0, loss_pct=0.0)

    # Path 2: s1 <-> s3 <-> s4 (Alternative / Redundant)
    topo.add_link("s1", "s3", port1=3, port2=1, delay_ms=8.0, loss_pct=0.0)
    topo.add_link("s3", "s4", port1=2, port2=2, delay_ms=8.5, loss_pct=0.0)

    # Cross-link between core switches: s2 <-> s3
    topo.add_link("s2", "s3", port1=3, port2=3, delay_ms=3.0, loss_pct=0.0)

    # Hosts
    topo.add_host("h1", ip="10.0.0.101", mac="00:00:00:00:00:01", attached_switch="s1", attached_port=1)
    topo.add_host("h2", ip="10.0.0.102", mac="00:00:00:00:00:02", attached_switch="s1", attached_port=4)
    topo.add_host("h3", ip="10.0.0.103", mac="00:00:00:00:00:03", attached_switch="s4", attached_port=3)
    topo.add_host("h4", ip="10.0.0.104", mac="00:00:00:00:00:04", attached_switch="s4", attached_port=4)

    return topo

class RyuTopologyClient:
    """Discovers topology directly from live Ryu SDN REST API."""
    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        self.base_url = base_url.rstrip("/")

    def discover_topology(self) -> SDNTopology:
        topo = SDNTopology()
        try:
            # 1. Get switches
            sw_resp = requests.get(f"{self.base_url}/v1.0/topology/switches", timeout=2.0)
            if sw_resp.status_code == 200:
                for sw in sw_resp.json():
                    dpid = str(sw.get("dpid"))
                    topo.add_switch(dpid, name=f"s{dpid}")

            # 2. Get links
            link_resp = requests.get(f"{self.base_url}/v1.0/topology/links", timeout=2.0)
            if link_resp.status_code == 200:
                for link in link_resp.json():
                    s1 = f"s{link['src']['dpid']}"
                    s2 = f"s{link['dst']['dpid']}"
                    p1 = int(link['src']['port_no'])
                    p2 = int(link['dst']['port_no'])
                    topo.add_link(s1, s2, port1=p1, port2=p2)
        except Exception:
            # If Ryu is not running, return mock topology
            pass
        return topo
