from . import packet as pkt


class UnreliableSender:
    def __init__(self, socket, remote_addr):
        self.socket = socket
        self.remote_addr = remote_addr
        self.next_seq = 0
        
        print("[UNRELIABLE_SENDER] Initialized")
    
    
    def send(self, payload):
        seq_no = self.next_seq
        
        packet_bytes = pkt.encode_data_packet(pkt.CHANNEL_UNRELIABLE, seq_no, payload)
        
        self.socket.sendto(packet_bytes, self.remote_addr)
        
        self.next_seq = (self.next_seq + 1) % pkt.MAX_SEQ_NUM
        
        print(f"[UNRELIABLE_SENDER] Sent seq={seq_no}")
        
        return seq_no
