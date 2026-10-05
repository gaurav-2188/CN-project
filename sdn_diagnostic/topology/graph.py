"""
SDN Network Topology representation and Graph calculations.
Supports live REST controllers (Ryu / ONOS) or simulated multi-switch topologies.
"""
import networkx as nx
from typing import List, Dict, Any, Optional

class SDNTopology:
    def __init__(self):
        # Multi-graph or directed graph for switches, links, and hosts
        self.graph = nx.Graph()
        self.switches: Dict[str, Dict[str, Any]] = {}
        self.links: List[Dict[str, Any]] = []
        self.hosts: Dict[str, Dict[str, Any]] = {}
        self.link_stats: Dict[str, Dict[str, Any]] = {}

    def add_switch(self, dpid: str, name: str = None, ip: str = None):
        name = name or f"s{dpid}"
        self.switches[dpid] = {"dpid": dpid, "name": name, "ip": ip}
        self.graph.add_node(name, node_type="switch", dpid=dpid)

    def add_host(self, host_id: str, ip: str, mac: str, attached_switch: str, attached_port: int):
        self.hosts[host_id] = {
            "id": host_id,
            "ip": ip,
            "mac": mac,
            "switch": attached_switch,
            "port": attached_port
        }
        self.graph.add_node(host_id, node_type="host", ip=ip, mac=mac)
        # Link host to switch
        self.add_link(host_id, attached_switch, port1=0, port2=attached_port, delay_ms=1.0, loss_pct=0.0)

    def add_link(self, node1: str, node2: str, port1: int = 1, port2: int = 1,
                 delay_ms: float = 5.0, loss_pct: float = 0.0, capacity_mbps: float = 1000.0, is_failed: bool = False):
        link_id = f"{node1}:{port1}<->{node2}:{port2}"
        link_meta = {
            "link_id": link_id,
            "src": node1,
            "dst": node2,
            "port1": port1,
            "port2": port2,
            "delay_ms": delay_ms,
            "loss_pct": loss_pct,
            "capacity_mbps": capacity_mbps,
            "is_failed": is_failed
        }
        self.links.append(link_meta)
        self.link_stats[link_id] = link_meta
        self.graph.add_edge(node1, node2, **link_meta)

    def set_link_status(self, link_id: str, is_failed: bool = None, delay_ms: float = None, loss_pct: float = None):
        """Allows dynamic fault injection (link down, high latency, drop)."""
        if link_id in self.link_stats:
            meta = self.link_stats[link_id]
            if is_failed is not None:
                meta["is_failed"] = is_failed
            if delay_ms is not None:
                meta["delay_ms"] = delay_ms
            if loss_pct is not None:
                meta["loss_pct"] = loss_pct
            
            src, dst = meta["src"], meta["dst"]
            if self.graph.has_edge(src, dst):
                self.graph[src][dst].update(meta)

    def get_all_paths(self, src_host: str, dst_host: str) -> List[List[str]]:
        """Finds all simple paths between two hosts."""
        if not self.graph.has_node(src_host) or not self.graph.has_node(dst_host):
            return []
        try:
            return list(nx.all_simple_paths(self.graph, source=src_host, target=dst_host))
        except Exception:
            return []

    def get_path_metrics(self, path: List[str]) -> Dict[str, Any]:
        """Calculates theoretical delay, cumulative loss, and identifies if any link is down along a path."""
        total_delay = 0.0
        success_rate = 1.0
        has_failed_link = False
        failed_links = []
        hop_links = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge_data = self.graph.get_edge_data(u, v) or {}
            delay = edge_data.get("delay_ms", 2.0)
            loss = edge_data.get("loss_pct", 0.0)
            is_failed = edge_data.get("is_failed", False)

            total_delay += delay
            success_rate *= (1.0 - (loss / 100.0))

            if is_failed:
                has_failed_link = True
                failed_links.append(f"{u} <-> {v}")

            hop_links.append({
                "from": u,
                "to": v,
                "delay_ms": delay,
                "loss_pct": loss,
                "is_failed": is_failed
            })

        total_loss_pct = round((1.0 - success_rate) * 100.0, 2)
        if has_failed_link:
            total_loss_pct = 100.0

        return {
            "path": path,
            "hop_count": len(path) - 1,
            "total_delay_ms": round(total_delay, 2),
            "expected_loss_pct": total_loss_pct,
            "is_viable": not has_failed_link,
            "failed_links": failed_links,
            "hops": hop_links
        }

    def serialize(self) -> Dict[str, Any]:
        """Serializes topology into JSON for visualization and UI."""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({
                "id": n,
                "label": n,
                "type": data.get("node_type", "switch"),
                "ip": data.get("ip", "")
            })
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "from": u,
                "to": v,
                "delay_ms": data.get("delay_ms", 0),
                "loss_pct": data.get("loss_pct", 0),
                "is_failed": data.get("is_failed", False)
            })
        return {"nodes": nodes, "edges": edges, "switches": self.switches, "hosts": self.hosts}
