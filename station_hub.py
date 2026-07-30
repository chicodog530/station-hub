import json
import os
import sys
import time
import sounddevice as sd

from hub.core.audio_engine import AudioEngine
from hub.servers.legacy_server import LegacyServer
from hub.servers.yar1_server import YAR1Server
from hub.servers.api_server import ApiServer
from hub.core.rig_controller import RigController
from hub.core.ptt_watchdog import PttWatchdog

CONFIG_FILE = "hub_config.json"

def load_config():
    default_config = {
        "in_dev": -1,
        "out_dev": -1,
        "legacy_port": 7373,
        "legacy_enabled": True,
        "yar1_port": 7374,
        "yar1_enabled": True,
        "api_port": 7375,
        "api_enabled": True,
        "bind_address": "0.0.0.0",
        "rig_host": "127.0.0.1",
        "rig_port": 4532
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                c = json.load(f)
                for k, v in default_config.items():
                    if k not in c: c[k] = v
                return c
        except Exception:
            pass
    return default_config

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

class StationHub:
    """
    Master orchestrator for the amateur radio ecosystem.
    Hosts Audio Relays and the Rig Control API.
    """
    def __init__(self, config):
        self.config = config
        self.running = False
        
        self.engine = None
        self.legacy_srv = None
        self.yar1_srv = None
        self.api_srv = None
        self.rig = None
        self.ptt = None

    def log(self, msg):
        print(f"[Hub] {msg}")

    def start(self):
        in_idx = self.config["in_dev"]
        out_idx = self.config["out_dev"]
        
        if in_idx < 0 or out_idx < 0:
            self.log("Invalid audio devices. Cannot start Audio Engine.")
            return
            
        self.running = True
        bind_addr = self.config["bind_address"]
        
        try:
            # 1. Start Audio Engine
            self.engine = AudioEngine(in_idx, out_idx, log_callback=self.log)
            self.engine.start()
            
            # 2. Start Rig Controller
            self.rig = RigController(host=self.config["rig_host"], port=self.config["rig_port"], log_callback=self.log)
            self.rig.start()
            
            # 3. Start PTT Watchdog
            self.ptt = PttWatchdog(self.rig, log_callback=self.log)
            self.ptt.start()
            
            # 4. Start Network Services
            if self.config["legacy_enabled"]:
                self.legacy_srv = LegacyServer(self.config["legacy_port"], self.engine, log_callback=self.log)
                self.legacy_srv.start(bind_addr)
                
            if self.config["yar1_enabled"]:
                self.yar1_srv = YAR1Server(self.config["yar1_port"], self.engine, log_callback=self.log)
                self.yar1_srv.start(bind_addr)
                
            if self.config["api_enabled"]:
                self.api_srv = ApiServer(self.config["api_port"], self.rig, self.ptt, log_callback=self.log)
                self.api_srv.start(bind_addr)
                
            self.log("Station Hub is active and listening.")
            
        except Exception as e:
            self.log(f"Fatal error starting Hub: {e}")
            self.stop()

    def stop(self):
        self.running = False
        if self.api_srv: self.api_srv.stop()
        if self.yar1_srv: self.yar1_srv.stop()
        if self.legacy_srv: self.legacy_srv.stop()
        if self.ptt: self.ptt.stop()
        if self.rig: self.rig.stop()
        if self.engine: self.engine.stop()
        self.log("Station Hub stopped.")

if __name__ == "__main__":
    c = load_config()
    
    if c["in_dev"] < 0 or c["out_dev"] < 0:
        print("Available devices:")
        print(sd.query_devices())
        try:
            c["in_dev"] = int(input("Enter Input Device ID (Radio RX): "))
            c["out_dev"] = int(input("Enter Output Device ID (Radio TX): "))
            save_config(c)
        except ValueError:
            print("Invalid input.")
            sys.exit(1)
            
    hub = StationHub(c)
    hub.start()
    
    try:
        while hub.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Hub...")
        hub.stop()
