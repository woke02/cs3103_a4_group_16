import time


class UnreliableReceiver:
    def __init__(self, delivery_callback):
        self.delivery_callback = delivery_callback
        
        print("[UNRELIABLE_RECEIVER] Initialized")
    
    
    def on_receive(self, packet_data):
        seq_no = packet_data['seq_no']
        timestamp = packet_data['timestamp']
        payload = packet_data['payload']
        
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
        
        print(f"[UNRELIABLE_RECEIVER] Delivered seq={seq_no} (latency={latency:.1f}ms)")
