"""
UDP Diagnostic Probe Client.
Sends sequences of UDP packets to measure RTT, loss, and jitter.
"""
import socket
import time
import math
from typing import Dict, Any, List
from sdn_diagnostic.probe.packet import ProbePacket

class UDPProbeClient:
    def __init__(self, target_host: str = "127.0.0.1", target_port: int = 9999, timeout: float = 1.0):
        self.target_host = target_host
        self.target_port = target_port
        self.timeout = timeout

    def run_probe(self, count: int = 10, interval_ms: float = 20.0, payload_size: int = 64) -> Dict[str, Any]:
        """
        Runs an active UDP probe train towards target_host:target_port.
        Returns detailed summary metrics: RTT stats, packet loss, jitter.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)

        sent_count = 0
        received_count = 0
        rtts = []
        inter_arrival_jitters = []
        last_transit_time = None

        packets_detail: List[Dict[str, Any]] = []

        for seq in range(count):
            pkt = ProbePacket(seq_id=seq, packet_type=ProbePacket.TYPE_PING, payload_size=payload_size)
            data = pkt.encode()
            t_send = time.time()
            
            try:
                sock.sendto(data, (self.target_host, self.target_port))
                sent_count += 1

                resp_data, _ = sock.recvfrom(4096)
                t_recv = time.time()
                resp_pkt = ProbePacket.decode(resp_data)

                rtt_ms = (t_recv - t_send) * 1000.0
                rtts.append(rtt_ms)
                received_count += 1

                # Calculate transit time and RFC 3550 jitter approximation
                transit_time = (t_recv - resp_pkt.send_time) * 1000.0
                if last_transit_time is not None:
                    d = abs(transit_time - last_transit_time)
                    inter_arrival_jitters.append(d)
                last_transit_time = transit_time

                packets_detail.append({
                    "seq": seq,
                    "status": "SUCCESS",
                    "rtt_ms": round(rtt_ms, 2)
                })

            except socket.timeout:
                packets_detail.append({
                    "seq": seq,
                    "status": "TIMEOUT",
                    "rtt_ms": None
                })
            except Exception as e:
                packets_detail.append({
                    "seq": seq,
                    "status": f"ERROR ({str(e)})",
                    "rtt_ms": None
                })

            if interval_ms > 0 and seq < count - 1:
                time.sleep(interval_ms / 1000.0)

        sock.close()

        # Compute aggregate metrics
        loss_pct = ((sent_count - received_count) / sent_count * 100.0) if sent_count > 0 else 0.0
        min_rtt = min(rtts) if rtts else 0.0
        max_rtt = max(rtts) if rtts else 0.0
        avg_rtt = (sum(rtts) / len(rtts)) if rtts else 0.0
        
        # Standard deviation of RTT
        if len(rtts) > 1:
            variance = sum((x - avg_rtt) ** 2 for x in rtts) / (len(rtts) - 1)
            stddev_rtt = math.sqrt(variance)
        else:
            stddev_rtt = 0.0

        # Mean jitter
        jitter_ms = (sum(inter_arrival_jitters) / len(inter_arrival_jitters)) if inter_arrival_jitters else 0.0

        return {
            "target": f"{self.target_host}:{self.target_port}",
            "packets_sent": sent_count,
            "packets_received": received_count,
            "packet_loss_pct": round(loss_pct, 2),
            "min_rtt_ms": round(min_rtt, 2),
            "max_rtt_ms": round(max_rtt, 2),
            "avg_rtt_ms": round(avg_rtt, 2),
            "stddev_rtt_ms": round(stddev_rtt, 2),
            "jitter_ms": round(jitter_ms, 2),
            "packets": packets_detail
        }
