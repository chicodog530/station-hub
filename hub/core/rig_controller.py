import threading
import queue
import time
import itertools
import psutil
import serial
import subprocess
from hub.backends.hamlib_backend import HamlibRigctldBackend
from hub.backends.backend import RigError

class RigController:
    """
    Wraps the HamlibRigctldBackend in a thread-safe command queue.
    Only one thread will ever write to the CAT port.
    """
    def __init__(self, host="127.0.0.1", port=4532, log_callback=None):
        self.backend = HamlibRigctldBackend(host, port, timeout=1.5)
        self.log = log_callback or print
        self.cmd_queue = queue.PriorityQueue()
        self.counter = itertools.count()
        self.running = False
        self.thread = None
        self.state_cache = {}
        
        # Callbacks for state changes
        self.on_state_change = None

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        self.log("RigController started.")

    def stop(self):
        self.running = False
        # Push a dummy item to unblock the queue
        self.cmd_queue.put((99, next(self.counter), "stop", None, None))
        if self.thread:
            self.thread.join(timeout=2.0)
        self.backend.close()
        self.log("RigController stopped.")

    def set_band(self, band_code: str, callback=None):
        self.cmd_queue.put((4, next(self.counter), "set_band", {"band_code": band_code}, callback))
        
    def set_power(self, on: bool, callback=None):
        self.cmd_queue.put((4, next(self.counter), "set_power", {"on": on}, callback))

    def _find_and_kill_rigctld(self):
        cmdline = None
        com_port = "COM3"
        baud = 38400
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if proc.info['name'] and 'rigctld.exe' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        for i, arg in enumerate(cmdline):
                            if arg == "-r" and i + 1 < len(cmdline): com_port = cmdline[i+1]
                            if arg == "-s" and i + 1 < len(cmdline): baud = int(cmdline[i+1])
                    proc.kill()
                    self.log(f"Killed rigctld.exe, args: {cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return cmdline, com_port, baud

    def _restart_rigctld(self, cmdline):
        if cmdline:
            try:
                # Use subprocess to launch without blocking
                subprocess.Popen(cmdline, creationflags=subprocess.CREATE_NO_WINDOW)
                self.log(f"Restarted rigctld: {' '.join(cmdline)}")
            except Exception as e:
                self.log(f"Failed to restart rigctld: {e}")

    def _worker_loop(self):
        connected = False
        while self.running:
            if not connected:
                try:
                    self.backend.connect()
                    connected = True
                    self.log("Hamlib CAT connected.")
                except RigError as e:
                    self.log(f"Connection failed: {e}")
                    time.sleep(2)
                    continue

            try:
                # Wait for command, or timeout to poll
                poll_interval = 0.25 if self.state_cache.get("ptt") else 1.0
                priority, _seq, cmd_type, args, callback = self.cmd_queue.get(timeout=poll_interval)
                if cmd_type == "stop": break
                
                try:
                    if cmd_type == "set_freq":
                        new_freq = self.backend.set_frequency(args['frequency_hz'])
                        self.state_cache['frequency_hz'] = new_freq
                        if callback: callback(True, {"frequency_hz": new_freq})
                        self._notify_state()
                    elif cmd_type == "set_band":
                        # Raw Yaesu FT-710 band select command (e.g., BS04;)
                        self.backend._command(rf"\send_cmd {args['band_code']}")
                        if callback: callback(True, {})
                        self._poll_state()
                    elif cmd_type == "set_power":
                        if args['on']:
                            cmdline, com_port, baud = self._find_and_kill_rigctld()
                            if not cmdline and hasattr(self, 'last_rigctld_cmdline'):
                                cmdline = self.last_rigctld_cmdline
                                com_port = getattr(self, 'last_rigctld_port', "COM3")
                                baud = getattr(self, 'last_rigctld_baud', 38400)
                            
                            # Windows takes a moment to release the COM port handle after killing the process
                            time.sleep(1.5)
                            
                            ser = None
                            for attempt in range(5):
                                try:
                                    ser = serial.Serial(com_port, baud, timeout=1.0)
                                    break
                                except Exception as e:
                                    self.log(f"Serial port not ready yet (attempt {attempt+1}): {e}")
                                    time.sleep(1.0)
                            
                            if ser:
                                try:
                                    for _ in range(5):
                                        ser.write(b"PS1;")
                                        time.sleep(0.1)
                                    ser.close()
                                    self.log(f"Sent raw PS1; wakeup to {com_port}")
                                except Exception as e:
                                    self.log(f"Failed to write to raw serial {com_port}: {e}")
                            else:
                                self.log(f"Failed to open raw serial {com_port} after retries. Is another app using it?")
                                
                            if cmdline:
                                self.log("Waiting 5 seconds for FT-710 to boot up before starting rigctld...")
                                time.sleep(5.0)
                                self._restart_rigctld(cmdline)
                                time.sleep(2.0)
                                connected = False # Force reconnect
                        else:
                            self.backend._command(rf"\send_cmd PS0;")
                            time.sleep(0.5)
                            cmdline, com_port, baud = self._find_and_kill_rigctld()
                            if cmdline:
                                self.last_rigctld_cmdline = cmdline
                                self.last_rigctld_port = com_port
                                self.last_rigctld_baud = baud
                            connected = False
                        
                        if callback: callback(True, {})
                    elif cmd_type == "set_mode":
                        new_mode = self.backend.set_mode(args['mode'])
                        self.state_cache['mode'] = new_mode
                        if callback: callback(True, {"mode": new_mode})
                        self._notify_state()
                    elif cmd_type == "set_ptt":
                        self.backend.set_ptt(args['enabled'])
                        self.state_cache['ptt'] = args['enabled']
                        if callback: callback(True, {"ptt": args['enabled']})
                        self._notify_state()
                        
                        # Immediately poll state after PTT change to update meters
                        self._poll_state()
                    elif cmd_type == "set_rf_power":
                        power_ratio = float(args['power_ratio'])
                        try:
                            watts = max(5, int(power_ratio * 100))
                            self.backend._command(rf"\send_cmd PC{watts:03d};")
                        except RigError:
                            self.backend.set_level("RFPOWER", power_ratio)
                        if callback: callback(True, {})
                    elif cmd_type == "set_tune":
                        # We isolate these commands because some radios don't return ACKs for raw commands,
                        # which causes rigctld to return a timeout or error, which previously skipped the next command.
                        try:
                            res = self.backend._command(r"\send_cmd AC001;")
                            self.log(f"ATU enable response: {res}")
                        except Exception as e:
                            self.log(f"ATU enable error (ignored): {e}")
                            
                        time.sleep(0.2)
                        
                        try:
                            res = self.backend._command(r"\send_cmd AC003;", override_timeout=15.0)
                            self.log(f"ATU start response: {res}")
                            self.tuning_lockout = time.time() + 15.0 # Lockout polling for 15 seconds
                        except Exception as e:
                            self.log(f"ATU start error (ignored): {e}")
                            
                        if callback: callback(True, {})
                except RigError as e:
                    self.log(f"Command error ({cmd_type}): {e}")
                    # Only drop connection if it's not a generic error like ENAVAIL
                    if "-11" not in str(e):
                        connected = False
                    if callback: callback(False, {"error": str(e)})

            except queue.Empty:
                if connected:
                    try:
                        if hasattr(self, "tuning_lockout") and time.time() < self.tuning_lockout:
                            pass # Skip polling while tuning to prevent radio freeze
                        else:
                            self._poll_state()
                    except RigError as e:
                        # If radio is off, polling will time out. Don't drop connection.
                        if not hasattr(self, "_last_poll_err") or time.time() - getattr(self, "_last_poll_err", 0) > 10:
                            self.log(f"Radio not responding to polling: {e}")
                            self._last_poll_err = time.time()

    def _poll_state(self):
        st = self.backend.get_state()
        adv = self.backend.get_advanced_state()
        
        # Bypass Hamlib's meters during TX for real-time FT-710 ALC and SWR
        if st.ptt:
            try:
                res_alc = self.backend._command(r"\send_cmd RM2;")
                res_swr = self.backend._command(r"\send_cmd RM3;")
                
                # Format: RM2150; where 150 is the raw value (000-255)
                if "RM2" in res_alc:
                    val_alc = int(res_alc.replace("RM2", "").replace(";", ""))
                    adv.levels['ALC'] = min(1.0, val_alc / 255.0) # Map 0-255 to 0.0-1.0
                
                if "RM3" in res_swr:
                    val_swr = int(res_swr.replace("RM3", "").replace(";", ""))
                    # Rough mapping for SWR 0-255 scale. 0 = 1.0, 255 = ~3.0+
                    adv.levels['SWR'] = 1.0 + (val_swr / 127.5) 
            except Exception as e:
                self.log(f"Raw meter error: {e}")

        changed = False
        
        if st.frequency_hz != self.state_cache.get('frequency_hz'):
            self.state_cache['frequency_hz'] = st.frequency_hz
            changed = True
        if st.mode != self.state_cache.get('mode'):
            self.state_cache['mode'] = st.mode
            changed = True
        if st.ptt != self.state_cache.get('ptt'):
            self.state_cache['ptt'] = st.ptt
            changed = True
            
        rf_power = adv.levels.get('RFPOWER', 0.0)
        swr = adv.levels.get('SWR', 1.0)
        alc = adv.levels.get('ALC', 0.0)
        tuning = adv.functions.get('TUN', False) or adv.functions.get('TUNER', False)
        
        if rf_power != self.state_cache.get('rf_power'):
            self.state_cache['rf_power'] = rf_power
            changed = True
        if swr != self.state_cache.get('swr'):
            self.state_cache['swr'] = swr
            changed = True
        if alc != self.state_cache.get('alc'):
            self.state_cache['alc'] = alc
            changed = True
        if tuning != self.state_cache.get('tuning'):
            self.state_cache['tuning'] = tuning
            changed = True
            
        if changed:
            self._notify_state()

    def _notify_state(self):
        if self.on_state_change:
            # We copy to avoid concurrent modification issues
            self.on_state_change(dict(self.state_cache))

    # --- Public Thread-Safe API ---
    def set_frequency(self, frequency_hz, callback=None):
        self.cmd_queue.put((4, next(self.counter), "set_freq", {"frequency_hz": frequency_hz}, callback))

    def set_mode(self, mode, callback=None):
        self.cmd_queue.put((4, next(self.counter), "set_mode", {"mode": mode}, callback))

    def set_rf_power(self, power, callback=None):
        self.cmd_queue.put((4, next(self.counter), "set_rf_power", {"power": power}, callback))

    def set_tune(self, enable, callback=None):
        self.cmd_queue.put((4, next(self.counter), "set_tune", {"enable": enable}, callback))
        
    def set_ptt(self, enabled, callback=None):
        # High priority for PTT OFF (1), Medium for PTT ON (2)
        priority = 2 if enabled else 1
        self.cmd_queue.put((priority, next(self.counter), "set_ptt", {"enabled": enabled}, callback))
