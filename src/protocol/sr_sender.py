import time
import threading
from . import packet as pkt

WINDOW_SIZE = 32
RETRY_INTERVAL = 0.200
MAX_RETRIES = 1


class PacketInfo:
    def __init__(self, packet_bytes):
        self.packet = packet_bytes
        self.first_send_time = time.time()
        self.last_send_time = self.first_send_time
        self.retry_count = 0
        self.acked = False
        self.skipped = False


class SRSender:
    def __init__(self, socket, remote_addr, sender_timeout=RETRY_INTERVAL):
        self.socket = socket
        self.remote_addr = remote_addr
        self.sender_timeout = sender_timeout
        
        self.send_base = 0
        self.next_seq = 0
        
        self.send_buffer = {}
        self.acked = set()
        self.timers = {}
        
        self.lock = threading.Lock()
        
        print(f"[SR_SENDER] Initialized (window={WINDOW_SIZE})")
    
    
    def send(self, payload):
        with self.lock:
            used = (self.next_seq - self.send_base) % pkt.MAX_SEQ_NUM
            if used >= WINDOW_SIZE:
                print(f"[SR_SENDER] Window full (base={self.send_base}, next={self.next_seq})")
                return None
            
            seq_no = self.next_seq
            
            packet_bytes = pkt.encode_data_packet(pkt.CHANNEL_RELIABLE, seq_no, payload)
            
            self.socket.sendto(packet_bytes, self.remote_addr)
            
            self.send_buffer[seq_no] = PacketInfo(packet_bytes)
            
            timer = threading.Timer(RETRY_INTERVAL, self._on_timeout, args=[seq_no])
            timer.daemon = True
            timer.start()
            self.timers[seq_no] = timer
            
            self.next_seq = (self.next_seq + 1) % pkt.MAX_SEQ_NUM
            
            print(f"[SR_SENDER] Sent seq={seq_no}, window=[{self.send_base}, {self.next_seq})")
            
            return seq_no
    
    
    def on_ack(self, ack_no):
        with self.lock:
            if ack_no in self.acked:
                print(f"[SR_SENDER] Duplicate ACK {ack_no}")
                return
            
            if ack_no not in self.send_buffer:
                print(f"[SR_SENDER] ACK {ack_no} not in buffer (already processed)")
                return
            
            pkt_info = self.send_buffer[ack_no]
            
            rtt = (time.time() - pkt_info.first_send_time) * 1000
            
            self.acked.add(ack_no)
            pkt_info.acked = True
            
            if ack_no in self.timers:
                self.timers[ack_no].cancel()
                del self.timers[ack_no]
            
            del self.send_buffer[ack_no]
            
            print(f"[SR_SENDER] ACK {ack_no} received (RTT={rtt:.1f}ms)")
            
            self._slide_window()
    
    
    def _on_timeout(self, seq_no):
        with self.lock:
            if seq_no in self.acked or seq_no not in self.send_buffer:
                return
            
            pkt_info = self.send_buffer[seq_no]
            
            if pkt_info.retry_count >= MAX_RETRIES:
                elapsed = time.time() - pkt_info.first_send_time
                print(f"[SR_SENDER] SKIP seq={seq_no} (max retries reached, elapsed={elapsed*1000:.0f}ms)")
                
                pkt_info.skipped = True
                
                if seq_no in self.timers:
                    self.timers[seq_no].cancel()
                    del self.timers[seq_no]
                
                del self.send_buffer[seq_no]
                
                self._slide_window()
                
            else:
                pkt_info.retry_count += 1
                pkt_info.last_send_time = time.time()
                
                self.socket.sendto(pkt_info.packet, self.remote_addr)
                
                elapsed = time.time() - pkt_info.first_send_time
                print(f"[SR_SENDER] RETRY seq={seq_no} (attempt={pkt_info.retry_count}, elapsed={elapsed*1000:.0f}ms)")
                
                timer = threading.Timer(self.sender_timeout, self._on_timeout, args=[seq_no])
                timer.daemon = True
                timer.start()
                self.timers[seq_no] = timer
    
    
    def _slide_window(self):
        old_base = self.send_base
        
        while self.send_base in self.acked or self.send_base not in self.send_buffer:
            if self.send_base == self.next_seq:
                break
            self.send_base = (self.send_base + 1) % pkt.MAX_SEQ_NUM
        
        if self.send_base != old_base:
            print(f"[SR_SENDER] Window slide: {old_base} → {self.send_base}")
    
    
    def get_window_space(self):
        with self.lock:
            used = (self.next_seq - self.send_base) % pkt.MAX_SEQ_NUM
            return WINDOW_SIZE - used
    
    
    def close(self):
        with self.lock:
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
            print("[SR_SENDER] Closed")
