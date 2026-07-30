import sounddevice as sd
import threading
import queue
import time

class AudioEngine:
    SAMPLE_RATE = 48000
    CHUNK_SIZE = 4096
    CHANNELS = 1
    DTYPE = 'int16'

    def __init__(self, in_dev, out_dev, log_callback=None):
        self.in_dev = in_dev
        self.out_dev = out_dev
        self.log_callback = log_callback or print
        self.stream = None
        self.running = False

        self.rx_subscribers = []  # List of callbacks for RX audio (Radio -> PC)
        self.tx_provider = None   # Function that provides TX audio (PC -> Radio)
        
        self.lock = threading.Lock()
        self.sample_counter = 0
        
        self.stats = {
            "audio_input_overflows": 0,
            "audio_output_underflows": 0
        }

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._hotplug_loop, daemon=True)
        self.thread.start()

    def _hotplug_loop(self):
        while self.running:
            if self.stream is None:
                try:
                    self.stream = sd.RawStream(
                        samplerate=self.SAMPLE_RATE,
                        blocksize=self.CHUNK_SIZE,
                        device=(self.in_dev, self.out_dev),
                        channels=self.CHANNELS,
                        dtype=self.DTYPE,
                        callback=self._audio_callback
                    )
                    self.stream.start()
                    self.log_callback("Audio stream hooked and running.")
                except Exception:
                    self.stream = None
                    time.sleep(2.0)  # Retry every 2 seconds
            else:
                if not self.stream.active:
                    self.log_callback("Audio stream lost (radio powered off?). Waiting to reconnect...")
                    try:
                        self.stream.close()
                    except:
                        pass
                    self.stream = None
                time.sleep(1.0)

    def stop(self):
        if not self.running: return
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.log_callback("Audio stream stopped.")

    def subscribe_rx(self, callback):
        with self.lock:
            if callback not in self.rx_subscribers:
                self.rx_subscribers.append(callback)

    def unsubscribe_rx(self, callback):
        with self.lock:
            if callback in self.rx_subscribers:
                self.rx_subscribers.remove(callback)

    def set_tx_provider(self, provider):
        """Only one client should be transmitting to the radio at a time."""
        with self.lock:
            self.tx_provider = provider

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        if not self.running: return
        
        if status.input_overflow:
            self.stats["audio_input_overflows"] += 1
        if status.output_underflow:
            self.stats["audio_output_underflows"] += 1

        in_bytes = bytes(indata)
        
        with self.lock:
            # 1. Distribute RX (Mic/Radio input) to all subscribers
            for sub in self.rx_subscribers:
                sub(in_bytes, self.sample_counter)
                
            # 2. Get TX (Speaker/Radio output) from provider
            provided_data = None
            if self.tx_provider:
                provided_data = self.tx_provider(frames)
                
            if provided_data and len(provided_data) == len(outdata):
                outdata[:] = provided_data
            elif provided_data and len(provided_data) < len(outdata):
                outdata[:len(provided_data)] = provided_data
                outdata[len(provided_data):] = b'\x00' * (len(outdata) - len(provided_data))
            else:
                outdata[:] = b'\x00' * len(outdata)
                
            self.sample_counter += frames
