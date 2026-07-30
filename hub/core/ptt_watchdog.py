import threading
import time

class PttWatchdog:
    """
    Ensures safe PTT operations by dropping PTT if the client drops offline
    or stops sending keepalives.
    """
    def __init__(self, rig_controller, log_callback=None):
        self.rig = rig_controller
        self.log = log_callback or print
        
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        self.ptt_active = False
        self.last_keepalive = 0.0
        self.timeout_s = 1.0  # Drop PTT if no keepalive for 1000ms

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.force_rx("Watchdog stopping")
        
    def keepalive(self):
        with self.lock:
            self.last_keepalive = time.time()
            
    def request_tx(self):
        with self.lock:
            self.last_keepalive = time.time()
            if not self.ptt_active:
                self.ptt_active = True
                self.rig.set_ptt(True)
                self.log("PTT Watchdog: TX Requested")

    def request_rx(self):
        with self.lock:
            if self.ptt_active:
                self.ptt_active = False
                self.rig.set_ptt(False)
                self.log("PTT Watchdog: RX Requested")

    def force_rx(self, reason="Emergency"):
        with self.lock:
            if self.ptt_active:
                self.ptt_active = False
                self.rig.set_ptt(False)
                self.log(f"PTT Watchdog: FORCE RX ({reason})")
                
    def _watchdog_loop(self):
        while self.running:
            time.sleep(0.1)
            with self.lock:
                if self.ptt_active:
                    if time.time() - self.last_keepalive > self.timeout_s:
                        self.log("PTT Watchdog: KEEPALIVE TIMEOUT EXCEEDED")
                        self.ptt_active = False
                        # Force PTT off immediately
                        self.rig.set_ptt(False)
