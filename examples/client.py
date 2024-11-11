import asyncio
from asyncwebsockets.client import connect

async def recv_msgs():
  while True:
    print(f'Received: {await ws.recv()}')

async def send_msgs():
  count=0
  while True:
    msg = f'Hello {count}'
    await ws.send(msg)
    print(f'Sent: {msg}')
    count +=1
    await asyncio.sleep_ms(10)

async def main():
  global ws
  ws = await connect('wss://echo.websocket.org/')
  asyncio.create_task(recv_msgs())
  asyncio.create_task(send_msgs())
  while True:
    #Keep one async thread open
    await asyncio.sleep(100)

asyncio.run(main())
