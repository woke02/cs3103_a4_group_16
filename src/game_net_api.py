import socket
import threading
import queue
from protocol import packet as pkt
from protocol.sr_sender import SRSender
from protocol.sr_receiver import SRReceiver
from protocol.unreliable_sender import UnreliableSender
from protocol.unreliable_receiver import UnreliableReceiver


class GameNetAPI:
    def __init__(self, role, local_port, remote_addr=None, sender_timeout=0.200, receiver_timeout=0.200):
        self.role = role
        self.remote_addr = remote_addr
        self.sender_timeout = sender_timeout
        self.receiver_timeout = receiver_timeout
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', local_port))
        
        self.delivery_queue = queue.Queue()
        
        if role == 'sender':
            if not remote_addr:
                raise ValueError("Sender requires remote_addr")
            
            self.reliable_sender = SRSender(
                self.socket, 
                remote_addr,
                sender_timeout=sender_timeout
            )
            self.unreliable_sender = UnreliableSender(
                self.socket,
                remote_addr
            )
            
            self.running = True
            self.recv_thread = threading.Thread(target=self._sender_recv_loop)
            self.recv_thread.daemon = True
            self.recv_thread.start()
            
            print(f"[GAME_NET_API] Initialized as SENDER (port={local_port}, remote={remote_addr})")
            
        else:
            self.reliable_receiver = SRReceiver(
                self.socket,
                lambda pkt: self._on_delivery(pkt, 'reliable'),
                receiver_timeout=receiver_timeout
            )
            self.unreliable_receiver = UnreliableReceiver(
                lambda pkt: self._on_delivery(pkt, 'unreliable')
            )
            
            self.running = True
            self.recv_thread = threading.Thread(target=self._receiver_recv_loop)
            self.recv_thread.daemon = True
            self.recv_thread.start()
            
            print(f"[GAME_NET_API] Initialized as RECEIVER (port={local_port})")
    
    
    # SEND API
    def send(self, data, reliable=True):
        if self.role != 'sender':
            raise RuntimeError("API is configured as receiver")
        
        if isinstance(data, str):
            payload = data.encode('utf-8')
        else:
            payload = data
        
        if reliable:
            return self.reliable_sender.send(payload)
        else:
            return self.unreliable_sender.send(payload)
    
    
    def _sender_recv_loop(self):
        while self.running:
            try:
                self.socket.settimeout(0.5)
                packet_bytes, addr = self.socket.recvfrom(2048)
                
                if pkt.is_ack_packet(packet_bytes):
                    ack_data = pkt.decode_ack_packet(packet_bytes)
                    self.reliable_sender.on_ack(ack_data['ack_no'])
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[SENDER_RECV] Error: {e}")
    
    
    # RECEIVE API
    def receive(self, timeout=None):
        if self.role != 'receiver':
            raise RuntimeError("API is configured as sender")
        
        try:
            return self.delivery_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    
    def _receiver_recv_loop(self):
        while self.running:
            try:
                self.socket.settimeout(0.5)
                packet_bytes, addr = self.socket.recvfrom(2048)
                
                if pkt.is_ack_packet(packet_bytes):
                    continue
                
                packet_data = pkt.decode_data_packet(packet_bytes)
                channel_type = packet_data['channel_type']
                
                if channel_type == pkt.CHANNEL_RELIABLE:
                    self.reliable_receiver.on_receive(packet_data, addr)
                elif channel_type == pkt.CHANNEL_UNRELIABLE:
                    self.unreliable_receiver.on_receive(packet_data)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[RECEIVER_RECV] Error: {e}")
    
    
    def _on_delivery(self, packet_info, channel):
        packet_info['channel'] = channel
        self.delivery_queue.put(packet_info)
    
    
    def close(self):
        print("[GAME_NET_API] Closing...")
        self.running = False
        
        if self.role == 'sender':
            self.reliable_sender.close()
        else:
            self.reliable_receiver.close()
        
        if self.recv_thread.is_alive():
            self.recv_thread.join(timeout=2)
        
        self.socket.close()
        print("[GAME_NET_API] Closed")
