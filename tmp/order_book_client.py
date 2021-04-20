import asyncio
import websockets

async def hello():
    uri = "wss://stream.binance.com:9443/ws/bnbbtc@depth5"
    async with websockets.connect(uri) as websocket:
        #while True:
        greeting = await websocket.recv()
        print(f"< {greeting}")

def run():
    asyncio.get_event_loop().run_until_complete(hello())
    asyncio.get_event_loop().run_forever()