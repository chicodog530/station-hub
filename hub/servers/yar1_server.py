import socket
import threading
import queue
import time
import hub.servers.protocol_yar1 as prot

class YAR1Server:
    def __init__(self, port, audio_engine, log_callback=None):
        self.port = port
        self.engine = audio_engine
        self.log = log_callback or print
        
        self.running = False
        self.server_socket = None
        self.thread = None
        self.active_conn = None
        
        # Larger jitter buffers for modem
        self.rx_queue = queue.Queue(maxsize=16) # Android -> Radio
        self.tx_queue = queue.Queue(maxsize=16) # Radio -> Android
        
        self.stats = {
            "rx_sequence": 0,
            "tx_sequence": 0,
            "network_rx_gaps": 0,
            "network_tx_gaps": 0
        }

    def start(self, bind_address='0.0.0.0'):
        if self.running: return
        self.running = True
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((bind_address, self.port))
        self.server_socket.listen(1)
        
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        self.log(f"YAR1 Server listening on {self.port}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        if self.active_conn:
            self.active_conn.close()

    def _audio_rx_callback(self, data, sample_counter):
        self.stats["tx_sequence"] += 1
        frame = prot.pack_header(prot.FT_AUDIO_TX, sequence=self.stats["tx_sequence"], timestamp=sample_counter, payload_length=len(data)) + data
        try:
            self.tx_queue.put_nowait(frame)
        except queue.Full:
            self.stats["network_tx_gaps"] += 1
            try: self.tx_queue.get_nowait()
            except queue.Empty: pass
            self.tx_queue.put_nowait(frame)

    def _audio_tx_provider(self, frames):
        try:
            return self.rx_queue.get_nowait()
        except queue.Empty:
            return None

    def _accept_loop(self):
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                conn, addr = self.server_socket.accept()
                self.active_conn = conn
                conn.settimeout(None)
                self.log(f"YAR1 client connected from {addr}")
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # Clear queues
                while not self.rx_queue.empty(): self.rx_queue.get()
                while not self.tx_queue.empty(): self.tx_queue.get()
                
                t1 = threading.Thread(target=self._network_read, args=(conn,), daemon=True)
                t2 = threading.Thread(target=self._network_write, args=(conn,), daemon=True)
                t1.start()
                t2.start()
                
                while self.running and t1.is_alive():
                    t1.join(1.0)
                    
                conn.close()
                self.active_conn = None
                self.engine.unsubscribe_rx(self._audio_rx_callback)
                self.engine.set_tx_provider(None)
                if self.running:
                    self.log("YAR1 client disconnected.")
            except socket.timeout:
                continue
            except socket.error:
                break

    def _recv_exact(self, conn, count):
        data = bytearray()
        while len(data) < count:
            if not self.running: return None
            try:
                conn.settimeout(1.0)
                chunk = conn.recv(count - len(data))
                if not chunk: return None
                data.extend(chunk)
            except socket.timeout:
                continue
            except:
                return None
        return bytes(data)

    def _network_read(self, conn):
        handshake_done = False
        try:
            while self.running:
                header_data = self._recv_exact(conn, 24)
                if not header_data: break
                
                magic, ftype, flags, res, seq, plen, ts = prot.unpack_header(header_data)
                
                payload = b''
                if plen > 0:
                    payload = self._recv_exact(conn, plen)
                    if payload is None: break
                
                if ftype == prot.FT_HELLO:
                    self.log("YAR1: Received HELLO")
                    handshake_done = True
                    conn.sendall(prot.pack_hello_ack())
                    if self.engine:
                        self.engine.subscribe_rx(self._audio_rx_callback)
                        self.engine.set_tx_provider(self._audio_tx_provider)
                elif ftype == prot.FT_AUDIO_RX:
                    if not handshake_done: continue
                    if self.stats["rx_sequence"] != 0 and seq != self.stats["rx_sequence"] + 1:
                        self.stats["network_rx_gaps"] += 1
                    self.stats["rx_sequence"] = seq
                    try:
                        self.rx_queue.put_nowait(payload)
                    except queue.Full:
                        try: self.rx_queue.get_nowait()
                        except: pass
                        self.rx_queue.put_nowait(payload)
                elif ftype == prot.FT_PING:
                    conn.sendall(prot.pack_header(prot.FT_PONG))
                
        except Exception as e:
            self.log(f"YAR1 read error: {e}")

    def _network_write(self, conn):
        try:
            while self.running:
                try:
                    data = self.tx_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                try:
                    conn.settimeout(1.0)
                    conn.sendall(data)
                except socket.timeout:
                    continue
        except Exception as e:
            self.log(f"YAR1 write error: {e}")
