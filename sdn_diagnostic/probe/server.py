"""
UDP Diagnostic Echo Server.
Runs in a background thread to answer probe queries.
"""
import socket
import threading
import time
import logging
from sdn_diagnostic.probe.packet import ProbePacket

logger = logging.getLogger(__name__)

class UDPEchoServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.running = False
        self.sock = None
        self.thread = None
        self.packets_received = 0
        self.packets_echoed = 0
        # Optional artificial impairments for test/sim
        self.artificial_delay_ms = 0.0
        self.artificial_drop_rate = 0.0

    def start(self):
        if self.running:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(0.5)
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"UDP Echo Server listening on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        logger.info("UDP Echo Server stopped.")

    def _run_loop(self):
        import random
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self.packets_received += 1
                
                # Check artificial drop simulation
                if self.artificial_drop_rate > 0:
                    if random.random() < self.artificial_drop_rate:
                        continue # Silently drop

                # Artificial delay simulation
                if self.artificial_delay_ms > 0:
                    time.sleep(self.artificial_delay_ms / 1000.0)

                pkt = ProbePacket.decode(data)
                pkt.packet_type = ProbePacket.TYPE_ECHO
                pkt.echo_time = time.time()
                
                resp = pkt.encode()
                self.sock.sendto(resp, addr)
                self.packets_echoed += 1
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.debug(f"Server exception: {e}")
