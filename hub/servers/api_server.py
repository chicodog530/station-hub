import asyncio
import websockets
import json
import threading

class ApiServer:
    """
    WebSocket server for remote Rig Control over JSON.
    """
    def __init__(self, port, rig_controller, ptt_watchdog, log_callback=None):
        self.port = port
        self.rig = rig_controller
        self.ptt = ptt_watchdog
        self.log = log_callback or print
        
        self.running = False
        self.thread = None
        self.loop = None
        self.clients = set()
        
        # Subscribe to rig state changes
        self.rig.on_state_change = self._broadcast_state

    def start(self, bind_address='0.0.0.0'):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, args=(bind_address,), daemon=True)
        self.thread.start()
        self.log(f"API Server listening on ws://{bind_address}:{self.port}")

    def stop(self):
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run_loop(self, bind_address):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def main():
            async with websockets.serve(self._handle_client, bind_address, self.port):
                await asyncio.Future()  # run forever

        try:
            self.loop.run_until_complete(main())
        except asyncio.CancelledError:
            pass
        finally:
            pending = asyncio.all_tasks(loop=self.loop)
            for task in pending: task.cancel()
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    async def _handle_client(self, websocket):
        self.clients.add(websocket)
        self.log(f"API client connected from {websocket.remote_address}")
        
        # Send initial state
        await self._send_json(websocket, {
            "type": "radio_state",
            **self.rig.state_cache
        })
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    req_id = data.get("request_id", "")
                    
                    if msg_type == "set_frequency":
                        hz = data.get("frequency_hz")
                        if hz:
                            self.rig.set_frequency(hz, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                            
                    elif msg_type == "set_band":
                        band = data.get("band_code")
                        if band:
                            self.rig.set_band(band, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                    elif msg_type == "set_power":
                        on = data.get("on", True)
                        self.rig.set_power(on, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                    elif msg_type == "set_ptt":
                        enabled = data.get("enabled", False)
                        self.rig.set_ptt(enabled, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                    elif msg_type == "set_mode":
                        mode = data.get("mode")
                        if mode:
                            self.rig.set_mode(mode, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                            
                    elif msg_type == "set_rf_power":
                        power = data.get("power")
                        if power is not None:
                            self.rig.set_rf_power(power, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                            
                    elif msg_type == "set_tune":
                        enable = data.get("enable")
                        if enable is not None:
                            self.rig.set_tune(enable, lambda s, r: self._send_result_sync(websocket, req_id, s, r))
                            
                    elif msg_type == "ptt_request_on":
                        self.ptt.request_tx()
                        await self._send_json(websocket, {"type": "command_result", "request_id": req_id, "success": True})
                        
                    elif msg_type == "ptt_keepalive":
                        self.ptt.keepalive()
                        
                    elif msg_type == "ptt_request_off":
                        self.ptt.request_rx()
                        await self._send_json(websocket, {"type": "command_result", "request_id": req_id, "success": True})
                        
                except json.JSONDecodeError:
                    self.log("Invalid JSON received")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            self.ptt.force_rx("Client disconnected")
            self.log("API client disconnected")

    async def _send_json(self, websocket, data):
        try:
            await websocket.send(json.dumps(data))
        except Exception:
            pass

    def _send_result_sync(self, websocket, req_id, success, result):
        # Called from RigController worker thread, must inject back to asyncio loop
        if self.loop and self.running:
            payload = {
                "type": "command_result",
                "request_id": req_id,
                "success": success,
                **result
            }
            asyncio.run_coroutine_threadsafe(self._send_json(websocket, payload), self.loop)

    def _broadcast_state(self, state):
        if self.loop and self.running and self.clients:
            payload = {
                "type": "radio_state",
                **state
            }
            # Create tasks for all clients
            async def broadcast():
                msg = json.dumps(payload)
                for client in list(self.clients):
                    try:
                        await client.send(msg)
                    except Exception:
                        pass
            asyncio.run_coroutine_threadsafe(broadcast(), self.loop)
