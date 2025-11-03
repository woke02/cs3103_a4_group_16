import time
import threading
from . import packet as pkt

WINDOW_SIZE = 32
DEFAULT_RECEIVER_SKIP_TIMEOUT = 0.200


class BufferedPacket:
    def __init__(self, payload, timestamp):
        self.payload = payload
        self.timestamp = timestamp
        self.arrival_time = time.time()


class SRReceiver:
    def __init__(self, socket, delivery_callback, receiver_timeout=DEFAULT_RECEIVER_SKIP_TIMEOUT):
        self.socket = socket
        self.delivery_callback = delivery_callback
        self.receiver_timeout = receiver_timeout
        
        self.rcv_base = 0
        
        self.rcv_buffer = {}
        self.delivered = set()
        self.waiting_since = {}
        
        self.lock = threading.Lock()
        
        self.running = True
        self.skip_checker = threading.Thread(target=self._check_skip_loop)
        self.skip_checker.daemon = True
        self.skip_checker.start()
        
        print(f"[SR_RECEIVER] Initialized (window={WINDOW_SIZE})")
    
    
    def on_receive(self, packet_data, sender_addr):
        seq_no = packet_data['seq_no']
        timestamp = packet_data['timestamp']
        payload = packet_data['payload']
        
        with self.lock:
            if seq_no in self.delivered:
                self._send_ack(seq_no, timestamp, sender_addr)
                print(f"[SR_RECEIVER] Duplicate seq={seq_no} (already delivered)")
                return
            
            if self._seq_less_than(seq_no, self.rcv_base):
                self._send_ack(seq_no, timestamp, sender_addr)
                print(f"[SR_RECEIVER] Old packet seq={seq_no} < rcv_base={self.rcv_base}")
                return
            
            if self._seq_greater_equal(seq_no, self.rcv_base + WINDOW_SIZE):
                print(f"[SR_RECEIVER] Reject seq={seq_no} (too far ahead, rcv_base={self.rcv_base})")
                return
            
            self._send_ack(seq_no, timestamp, sender_addr)
            
            if seq_no == self.rcv_base:
                if self.rcv_base in self.waiting_since:
                    del self.waiting_since[self.rcv_base]
                
                self._deliver_packet(seq_no, payload, timestamp)
                self.rcv_base = (self.rcv_base + 1) % pkt.MAX_SEQ_NUM
                
                print(f"[SR_RECEIVER] IN_ORDER seq={seq_no}, rcv_base→{self.rcv_base}")
                
                self._deliver_buffered()
                
            else:
                self.rcv_buffer[seq_no] = BufferedPacket(payload, timestamp)
                
                if self.rcv_base not in self.waiting_since:
                    self.waiting_since[self.rcv_base] = time.time()
                
                print(f"[SR_RECEIVER] BUFFER seq={seq_no} (waiting for {self.rcv_base}, buffer_size={len(self.rcv_buffer)})")
    
    
    def _deliver_packet(self, seq_no, payload, timestamp):
        self.delivered.add(seq_no)
        
        arrival_time = int(time.time() * 1000) & 0xFFFFFFFF
        if arrival_time >= timestamp:
            latency = arrival_time - timestamp
        else:
            latency = (0xFFFFFFFF - timestamp) + arrival_time + 1
        
        packet_info = {
            'seq_no': seq_no,
            'payload': payload,
            'timestamp': timestamp,
            'latency': latency
        }
        self.delivery_callback(packet_info)
    
    
    def _deliver_buffered(self):
        while self.rcv_base in self.rcv_buffer:
            buffered_pkt = self.rcv_buffer[self.rcv_base]
            
            self._deliver_packet(self.rcv_base, buffered_pkt.payload, buffered_pkt.timestamp)
            
            del self.rcv_buffer[self.rcv_base]
            
            if self.rcv_base in self.waiting_since:
                del self.waiting_since[self.rcv_base]
            
            print(f"[SR_RECEIVER] DELIVER_BUFFERED seq={self.rcv_base}")
            
            self.rcv_base = (self.rcv_base + 1) % pkt.MAX_SEQ_NUM
    
    
    def _send_ack(self, ack_no, timestamp, addr):
        ack_packet = pkt.encode_ack_packet(ack_no, timestamp)
        self.socket.sendto(ack_packet, addr)
    
    
    def _check_skip_loop(self):
        while self.running:
            time.sleep(0.020)
            
            with self.lock:
                if self.rcv_base in self.waiting_since:
                    wait_time = time.time() - self.waiting_since[self.rcv_base]
                    
                    if wait_time >= self.receiver_timeout:
                        print(f"[SR_RECEIVER] SKIP rcv_base={self.rcv_base} (waited {wait_time*1000:.0f}ms, buffer_size={len(self.rcv_buffer)})")
                        
                        del self.waiting_since[self.rcv_base]
                        
                        self.rcv_base = (self.rcv_base + 1) % pkt.MAX_SEQ_NUM
                        
                        self._deliver_buffered()
    
    
    def _seq_less_than(self, seq_a, seq_b):
        diff = (seq_a - seq_b) % pkt.MAX_SEQ_NUM
        return diff > pkt.MAX_SEQ_NUM // 2
    
    
    def _seq_greater_equal(self, seq_a, seq_b):
        diff = (seq_a - seq_b) % pkt.MAX_SEQ_NUM
        return diff < pkt.MAX_SEQ_NUM // 2
    
    
    def close(self):
        self.running = False
        if self.skip_checker.is_alive():
            self.skip_checker.join(timeout=1)
        print("[SR_RECEIVER] Closed")
