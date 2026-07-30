import asyncio
import websockets
import json

async def test_api():
    uri = "ws://127.0.0.1:7375"
    print(f"Connecting to Station Hub at {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!\n")
            
            # Wait for the initial radio_state message
            state_msg = await websocket.recv()
            print(f"Received initial state: {state_msg}\n")
            
            # Send a command to change frequency
            print("Sending command to change frequency to 14.250 MHz...")
            cmd = {
                "type": "set_frequency",
                "request_id": "test_1",
                "frequency_hz": 14250000
            }
            await websocket.send(json.dumps(cmd))
            
            # Wait for the command result
            result_msg = await websocket.recv()
            print(f"Received result: {result_msg}\n")
            
            # Wait for the updated radio_state message
            state_msg = await websocket.recv()
            print(f"Received updated state: {state_msg}\n")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
