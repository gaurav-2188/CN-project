"""
Correlation Engine & Path Analysis.
Correlates application-layer UDP socket measurements with SDN network paths.
Identifies faulty/degraded links and recommends optimal alternate paths.
"""
from typing import Dict, Any, List
from sdn_diagnostic.topology.graph import SDNTopology

class PathCorrelator:
    def __init__(self, topology: SDNTopology):
        self.topology = topology

    def analyze_path_correlation(
        self,
        src_host: str,
        dst_host: str,
        probe_results: Dict[str, Any],
        active_path: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes probe results against the SDN topology:
        - Evaluates the active path.
        - Attributes packet loss and delay anomalies to specific links.
        - Identifies all alternative paths and ranks them.
        """
        all_paths = self.topology.get_all_paths(src_host, dst_host)
        
        # Default active path: primary/shortest path if not explicitly provided
        if not active_path:
            active_path = all_paths[0] if all_paths else []

        active_path_metrics = self.topology.get_path_metrics(active_path) if active_path else {}

        # Observed metrics from UDP socket probe
        measured_loss_pct = probe_results.get("packet_loss_pct", 0.0)
        measured_rtt = probe_results.get("avg_rtt_ms", 0.0)

        # Fault Identification & Link Attribution
        fault_diagnosis = []
        is_path_degraded = False
        is_path_failed = False

        if not active_path_metrics.get("is_viable", True) or measured_loss_pct >= 99.0:
            is_path_failed = True
            fault_diagnosis.append(f"CRITICAL: Active path {active_path} is DOWN (100% loss).")
            if active_path_metrics.get("failed_links"):
                fault_diagnosis.append(f"Failed Link(s) Detected: {', '.join(active_path_metrics['failed_links'])}")
        elif measured_loss_pct > 5.0:
            is_path_degraded = True
            fault_diagnosis.append(f"WARNING: High packet loss ({measured_loss_pct}%) detected on path.")
            # Check links with drop simulation or congestion
            for hop in active_path_metrics.get("hops", []):
                if hop.get("loss_pct", 0) > 0:
                    fault_diagnosis.append(f"Attributed Drop Link: {hop['from']} <-> {hop['to']} has {hop['loss_pct']}% drop rate.")

        # Latency inflation check
        expected_rtt = (active_path_metrics.get("total_delay_ms", 0.0) * 2.0)
        if measured_rtt > (expected_rtt * 1.5) and expected_rtt > 0:
            is_path_degraded = True
            fault_diagnosis.append(
                f"LATENCY ANOMALY: Observed RTT ({measured_rtt}ms) exceeds expected baseline ({round(expected_rtt, 1)}ms)."
            )

        # Alternative Paths Comparison
        alternative_paths_eval = []
        best_alternate_path = None
        min_cost = float("inf")

        for p in all_paths:
            if p == active_path:
                continue
            meta = self.topology.get_path_metrics(p)
            # Cost function: prioritize viable path, then lowest loss, then lowest delay
            if meta["is_viable"]:
                cost = (meta["expected_loss_pct"] * 100) + meta["total_delay_ms"]
                if cost < min_cost:
                    min_cost = cost
                    best_alternate_path = p
            
            alternative_paths_eval.append({
                "path": p,
                "hop_count": meta["hop_count"],
                "expected_delay_ms": meta["total_delay_ms"],
                "expected_loss_pct": meta["expected_loss_pct"],
                "is_viable": meta["is_viable"],
                "failed_links": meta["failed_links"]
            })

        # Recommendation
        recommendation = "Maintain current active path."
        if is_path_failed or is_path_degraded:
            if best_alternate_path:
                recommendation = f"REROUTE RECOMMENDED: Switch active flow to healthy alternative path: {' -> '.join(best_alternate_path)}"
            else:
                recommendation = "ALERT: No viable alternative path found in SDN topology."

        return {
            "source_host": src_host,
            "destination_host": dst_host,
            "active_path": active_path,
            "active_path_status": "FAILED" if is_path_failed else ("DEGRADED" if is_path_degraded else "HEALTHY"),
            "measured_probe_metrics": {
                "avg_rtt_ms": measured_rtt,
                "packet_loss_pct": measured_loss_pct,
                "jitter_ms": probe_results.get("jitter_ms", 0.0)
            },
            "fault_diagnosis": fault_diagnosis,
            "recommendation": recommendation,
            "alternative_paths": alternative_paths_eval
        }
