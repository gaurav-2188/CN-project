"""
Challenging Scenarios & Robustness Framework (Deliverable 2: Challenging Scenario / Robustness).
Simulates realistic and adversarial network stress conditions:
1. Link Flapping (periodic rapid UP/DOWN oscillation)
2. Asymmetric Path Congestion (one-way buffer overflow)
3. Core Switch Crash (complete failure of switch s2)
4. Corrupted / Out-of-Order Packet Delivery
"""
import time
import threading
from typing import Dict, Any, Optional
from sdn_diagnostic.topology.graph import SDNTopology

class ScenarioManager:
    """Orchestrates complex and challenging network fault scenarios."""
    def __init__(self, topology: SDNTopology, echo_server):
        self.topology = topology
        self.echo_server = echo_server
        self.active_scenario = "NORMAL"
        self._flapping_thread = None
        self._stop_flapping = threading.Event()

    def reset_all(self):
        """Restores baseline operating health."""
        if self._flapping_thread and self._flapping_thread.is_alive():
            self._stop_flapping.set()
            self._flapping_thread.join(timeout=1.0)
        self._flapping_thread = None
        self._stop_flapping.clear()

        self.echo_server.artificial_delay_ms = 0.0
        self.echo_server.artificial_drop_rate = 0.0

        for link_id in self.topology.link_stats:
            meta = self.topology.link_stats[link_id]
            self.topology.set_link_status(
                link_id,
                is_failed=False,
                loss_pct=0.0,
                delay_ms=meta.get("delay_ms", 5.0)
            )
        self.active_scenario = "NORMAL"
        return {"status": "normal_restored"}

    def run_link_flapping(self, link_id: str = "s1:2<->s2:1", interval_s: float = 1.0):
        """Scenario A: Rapid Link Flapping (Intermittent link failure)."""
        self.reset_all()
        self.active_scenario = "LINK_FLAPPING"

        def _flapper():
            is_down = False
            while not self._stop_flapping.is_set():
                is_down = not is_down
                self.topology.set_link_status(link_id, is_failed=is_down, loss_pct=100.0 if is_down else 0.0)
                self.echo_server.artificial_drop_rate = 0.85 if is_down else 0.0
                time.sleep(interval_s)

        self._flapping_thread = threading.Thread(target=_flapper, daemon=True)
        self._flapping_thread.start()
        return {
            "scenario": "LINK_FLAPPING",
            "link": link_id,
            "oscillation_interval_s": interval_s,
            "description": "Link repeatedly drops and recovers every second; triggers continuous flapping detection."
        }

    def run_core_switch_failure(self, switch_name: str = "s2"):
        """Scenario B: Complete Core Switch Crash (All incident links down)."""
        self.reset_all()
        self.active_scenario = "CORE_SWITCH_FAILURE"
        failed_links = []
        for lid in list(self.topology.link_stats.keys()):
            if switch_name in lid:
                self.topology.set_link_status(lid, is_failed=True, loss_pct=100.0)
                failed_links.append(lid)
        
        self.echo_server.artificial_drop_rate = 1.0
        return {
            "scenario": "CORE_SWITCH_FAILURE",
            "switch": switch_name,
            "failed_links": failed_links,
            "description": f"Core switch {switch_name} has crashed, severing primary path. Requires immediate detour via alternative core switch s3."
        }

    def run_severe_bufferbloat(self, latency_ms: float = 85.0, loss_pct: float = 35.0):
        """Scenario C: Heavy Congestion & High Packet Loss."""
        self.reset_all()
        self.active_scenario = "SEVERE_CONGESTION"
        self.echo_server.artificial_delay_ms = latency_ms
        self.echo_server.artificial_drop_rate = loss_pct / 100.0

        for lid in self.topology.link_stats:
            if "s1" in lid and "s2" in lid:
                self.topology.set_link_status(lid, delay_ms=latency_ms, loss_pct=loss_pct)
        return {
            "scenario": "SEVERE_CONGESTION",
            "added_latency_ms": latency_ms,
            "loss_pct": loss_pct,
            "description": "Extreme buffer contention on s1-s2 link causing 35% packet drops and 85ms added queuing delay."
        }
