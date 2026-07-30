import socket
import threading
import queue

class LegacyServer:
    def __init__(self, port, audio_engine, log_callback=None):
        self.port = port
        self.engine = audio_engine
        self.log = log_callback or print
        
        self.running = False
        self.server_socket = None
        self.thread = None
        self.active_conn = None
        
        self.rx_queue = queue.Queue(maxsize=10) # from Android to Radio (play)
        self.tx_queue = queue.Queue(maxsize=2)  # from Radio to Android (record)

    def start(self, bind_address='0.0.0.0'):
        if self.running: return
        self.running = True
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((bind_address, self.port))
        self.server_socket.listen(1)
        
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        self.log(f"Legacy Server listening on {self.port}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        if self.active_conn:
            self.active_conn.close()

    def _audio_rx_callback(self, data, sample_counter):
        # We received data from physical mic, push to network queue
        try:
            self.tx_queue.put_nowait(data)
        except queue.Full:
            try: self.tx_queue.get_nowait()
            except queue.Empty: pass
            self.tx_queue.put_nowait(data)

    def _audio_tx_provider(self, frames):
        # We need to provide data to physical speakers from network queue
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
                self.log(f"Legacy client connected from {addr}")
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                # Clear queues
                while not self.rx_queue.empty(): self.rx_queue.get()
                while not self.tx_queue.empty(): self.tx_queue.get()
                
                # Register with Audio Engine
                # Only hook up audio if the engine is running
                if self.engine:
                    self.engine.subscribe_rx(self._audio_rx_callback)
                    self.engine.set_tx_provider(self._audio_tx_provider)
                
                t1 = threading.Thread(target=self._network_read, args=(conn,), daemon=True)
                t2 = threading.Thread(target=self._network_write, args=(conn,), daemon=True)
                t1.start()
                t2.start()
                
                while self.running and t1.is_alive():
                    t1.join(1.0)
                try:
                    conn.close()
                except:
                    pass
                if self.engine:
                    self.engine.unsubscribe_rx(self._audio_rx_callback)
                    self.engine.set_tx_provider(None)
                if self.running:
                    self.log("Legacy client disconnected.")
            except socket.timeout:
                continue
            except socket.error:
                break

    def _network_read(self, conn):
        try:
            while self.running:
                chunk_size = self.engine.CHUNK_SIZE if self.engine else 4096
                data = bytearray()
                while len(data) < chunk_size * 2:
                    if not self.running: return
                    try:
                        conn.settimeout(1.0)
                        chunk = conn.recv((self.engine.CHUNK_SIZE * 2) - len(data))
                        if not chunk: break
                        data.extend(chunk)
                    except socket.timeout:
                        continue
                    except:
                        break
                if not data or len(data) < self.engine.CHUNK_SIZE * 2:
                    break
                
                try:
                    self.rx_queue.put_nowait(bytes(data))
                except queue.Full:
                    try: self.rx_queue.get_nowait()
                    except queue.Empty: pass
                    self.rx_queue.put_nowait(bytes(data))
        except Exception as e:
            self.log(f"Legacy read error: {e}")

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
            self.log(f"Legacy write error: {e}")
