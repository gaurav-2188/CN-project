# Network Diagnostic and Path Analysis Tool (UDP)

A socket-based network diagnostic and path analysis tool that measures delay, packet loss, and jitter using UDP probes, and correlates them with SDN network topology to detect failures and evaluate alternative paths.

---

## 🚀 Quick Start (Interactive Web UI with 1-Click Buttons)

Start the web application:
```bash
python3 -m sdn_diagnostic.app
```
Then open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

### Features in the Web UI:
- **⚡ 1-Click UDP Path Probe**: Sends a burst of UDP datagrams between source & destination hosts and computes RTT, jitter, and packet loss %.
- **⚠️ 1-Click Congestion Simulation**: Injects 25% drop rate and 40ms added latency on the active link `s1 <-> s2`.
- **💥 1-Click Link Break**: Simulates an abrupt link failure on `s2 <-> s4`.
- **🔄 Reset Topology**: Clears all simulated faults and restores baseline health.
- **Interactive SDN Topology Graph**: Dynamically updates link colors (Green for healthy, Amber for degraded, Red for failed) and shows candidate/alternate paths.
- **Reroute Recommendations**: Correlates degraded path segments and suggests optimal backup paths.

---

## 💻 CLI Usage
You can also run diagnostics purely from the terminal:
```bash
python3 -m sdn_diagnostic.cli
```
