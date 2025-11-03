import socket
import threading
import queue
import time
import json
import os
from .protocol import packet as pkt
from .protocol.sr_sender import SRSender
from .protocol.sr_receiver import SRReceiver
from .protocol.unreliable_sender import UnreliableSender
from .protocol.unreliable_receiver import UnreliableReceiver


class GameNetAPI:
    def __init__(self, role, local_port, remote_addr=None, sender_timeout=0.200, receiver_timeout=0.200):
        self.role = role
        self.remote_addr = remote_addr
        self.sender_timeout = sender_timeout
        self.receiver_timeout = receiver_timeout
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', local_port))
        
        self.delivery_queue = queue.Queue()
        
        self.sent_packets = {} 
        self.received_packets = {} 
        self.tracking_lock = threading.Lock()
        
        self._load_tracking_data()
        
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
    
    
    def send(self, data, reliable=True):
        if self.role != 'sender':
            raise RuntimeError("API is configured as receiver")
        
        if isinstance(data, str):
            payload = data.encode('utf-8')
        else:
            payload = data
        
        if reliable:
            seq_no = self.reliable_sender.send(payload)
        else:
            seq_no = self.unreliable_sender.send(payload)
        
        with self.tracking_lock:
            self.sent_packets[seq_no] = {
                'timestamp': time.time(),
                'reliable': reliable,
                'acked': False
            }
            self._save_tracking_data()
        
        return seq_no
    
    def _sender_recv_loop(self):
        while self.running:
            try:
                self.socket.settimeout(0.5)
                packet_bytes, addr = self.socket.recvfrom(2048)
                
                if pkt.is_ack_packet(packet_bytes):
                    ack_data = pkt.decode_ack_packet(packet_bytes)
                    self.reliable_sender.on_ack(ack_data['ack_no'])
                    
                    with self.tracking_lock:
                        if ack_data['ack_no'] in self.sent_packets:
                            self.sent_packets[ack_data['ack_no']]['acked'] = True
                            self._save_tracking_data()
                
            except socket.timeout:
                continue
            except ConnectionResetError:
                if self.running:
                    print(f"[SENDER_RECV] Receiver disconnected")
                continue
            except OSError as e:
                if e.winerror == 10054:  # Connection forcibly closed by remote host
                    if self.running:
                        print(f"[SENDER_RECV] Receiver disconnected (Windows error 10054)")
                    continue
                else:
                    if self.running:
                        print(f"[SENDER_RECV] Socket error: {e}")
                continue
            except Exception as e:
                if self.running:
                    print(f"[SENDER_RECV] Unexpected error: {e}")

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
            except ConnectionResetError:
                if self.running:
                    print(f"[RECEIVER_RECV] Sender disconnected")
                continue
            except OSError as e:
                if e.winerror == 10054:  # Connection forcibly closed by remote host
                    if self.running:
                        print(f"[RECEIVER_RECV] Sender disconnected (Windows error 10054)")
                    continue
                else:
                    if self.running:
                        print(f"[RECEIVER_RECV] Socket error: {e}")
                continue
            except Exception as e:
                if self.running:
                    print(f"[RECEIVER_RECV] Unexpected error: {e}")
    
    
    def _on_delivery(self, packet_info, channel):
        packet_info['channel'] = channel
        
        with self.tracking_lock:
            self.received_packets[packet_info['seq_no']] = {
                'timestamp': time.time(),
                'reliable': (channel == 'reliable'),
                'latency': packet_info['latency']
            }
            self._save_tracking_data()
        
        self.delivery_queue.put(packet_info)
    
    def get_delivery_stats(self):
        """
        Calculate packet delivery statistics.
        
        Returns:
            dict: Statistics including delivery ratios and packet counts
        """
        with self.tracking_lock:
            all_sent = self._load_sent_packets_global()
            all_received = self._load_received_packets_global()
            
            stats = {
                'total_sent': len(all_sent),
                'total_received': len(all_received),
                'reliable_sent': sum(1 for p in all_sent.values() if p.get('reliable', True)),
                'reliable_received': sum(1 for p in all_received.values() if p.get('reliable', True)),
                'unreliable_sent': sum(1 for p in all_sent.values() if not p.get('reliable', True)),
                'unreliable_received': sum(1 for p in all_received.values() if not p.get('reliable', True)),
                'overall_delivery_ratio': 0.0,
                'reliable_delivery_ratio': 0.0,
                'unreliable_delivery_ratio': 0.0,
                'lost_packets': []
            }
            
            if stats['total_sent'] > 0:
                stats['overall_delivery_ratio'] = (stats['total_received'] / stats['total_sent']) * 100
            
            if stats['reliable_sent'] > 0:
                stats['reliable_delivery_ratio'] = (stats['reliable_received'] / stats['reliable_sent']) * 100
            
            if stats['unreliable_sent'] > 0:
                stats['unreliable_delivery_ratio'] = (stats['unreliable_received'] / stats['unreliable_sent']) * 100
            
            for seq_no, sent_info in all_sent.items():
                if seq_no not in all_received:
                    stats['lost_packets'].append({
                        'seq_no': seq_no,
                        'reliable': sent_info.get('reliable', True),
                        'timestamp': sent_info.get('timestamp', 0)
                    })
            
            return stats
    
    def _load_tracking_data(self):
        """Load packet tracking data from files."""
        tracking_dir = 'packet_tracking'
        os.makedirs(tracking_dir, exist_ok=True)
        
        if self.role == 'sender':
            sent_file = os.path.join(tracking_dir, 'sent_packets.json')
            if os.path.exists(sent_file):
                try:
                    with open(sent_file, 'r') as f:
                        data = json.load(f)
                        self.sent_packets = {int(k): v for k, v in data.get('packets', {}).items()}
                except (json.JSONDecodeError, IOError):
                    pass
        else:
            received_file = os.path.join(tracking_dir, 'received_packets.json')
            if os.path.exists(received_file):
                try:
                    with open(received_file, 'r') as f:
                        data = json.load(f)
                        self.received_packets = {int(k): v for k, v in data.get('packets', {}).items()}
                except (json.JSONDecodeError, IOError):
                    pass
    
    def _save_tracking_data(self):
        """Save packet tracking data to files."""
        tracking_dir = 'packet_tracking'
        os.makedirs(tracking_dir, exist_ok=True)
        
        if self.role == 'sender':
            sent_file = os.path.join(tracking_dir, 'sent_packets.json')
            try:
                with open(sent_file, 'w') as f:
                    json.dump({
                        'session_start': time.time(),
                        'packets': {str(k): v for k, v in self.sent_packets.items()}
                    }, f, indent=2)
            except IOError:
                pass
        else:
            received_file = os.path.join(tracking_dir, 'received_packets.json')
            try:
                with open(received_file, 'w') as f:
                    json.dump({
                        'session_start': time.time(), 
                        'packets': {str(k): v for k, v in self.received_packets.items()}
                    }, f, indent=2)
            except IOError:
                pass
    
    def _load_sent_packets_global(self):
        """Load all sent packets from global tracking file."""
        sent_file = os.path.join('packet_tracking', 'sent_packets.json')
        if os.path.exists(sent_file):
            try:
                with open(sent_file, 'r') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.get('packets', {}).items()}
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def _load_received_packets_global(self):
        """Load all received packets from global tracking file."""
        received_file = os.path.join('packet_tracking', 'received_packets.json')
        if os.path.exists(received_file):
            try:
                with open(received_file, 'r') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.get('packets', {}).items()}
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def clear_tracking_data(self):
        """Clear packet tracking files."""
        tracking_dir = 'packet_tracking'
        files_to_clear = ['sent_packets.json', 'received_packets.json']
        
        for filename in files_to_clear:
            file_path = os.path.join(tracking_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        
        # Clear in-memory tracking
        with self.tracking_lock:
            self.sent_packets.clear()
            self.received_packets.clear()
    
    def close(self):
        print("[GAME_NET_API] Closing...")
        self.running = False
        
        # Save final tracking data
        self._save_tracking_data()
        
        if self.role == 'sender':
            self.reliable_sender.close()
        else:
            self.reliable_receiver.close()
        
        if self.recv_thread.is_alive():
            self.recv_thread.join(timeout=2)
        
        self.socket.close()
        print("[GAME_NET_API] Closed")
