"""
UDP Diagnostic Packet representation and serialization.
"""
import json
import time

class ProbePacket:
    TYPE_PING = "PING"
    TYPE_ECHO = "ECHO"
    TYPE_TRACE = "TRACE"

    def __init__(self, seq_id: int, packet_type: str = TYPE_PING, payload_size: int = 64, send_time: float = None):
        self.seq_id = seq_id
        self.packet_type = packet_type
        self.payload_size = payload_size
        self.send_time = send_time or time.time()
        self.echo_time = 0.0

    def encode(self) -> bytes:
        data = {
            "seq": self.seq_id,
            "type": self.packet_type,
            "t_send": self.send_time,
            "t_echo": self.echo_time
        }
        encoded = json.dumps(data).encode("utf-8")
        # Pad if needed to match requested payload_size
        if len(encoded) < self.payload_size:
            padding = b"X" * (self.payload_size - len(encoded))
            encoded += padding
        return encoded

    @classmethod
    def decode(cls, raw_bytes: bytes) -> "ProbePacket":
        # Extract valid JSON prefix before padding if present
        raw_str = raw_bytes.decode("utf-8", errors="ignore")
        # Find closing brace of JSON object
        brace_idx = raw_str.rfind("}")
        if brace_idx == -1:
            raise ValueError("Malformed probe packet")
        json_str = raw_str[:brace_idx + 1]
        data = json.loads(json_str)
        pkt = cls(
            seq_id=data["seq"],
            packet_type=data.get("type", cls.TYPE_PING),
            payload_size=len(raw_bytes),
            send_time=data.get("t_send", 0.0)
        )
        pkt.echo_time = data.get("t_echo", 0.0)
        return pkt
