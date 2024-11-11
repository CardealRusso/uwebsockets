import socket, ssl, asyncio, binascii, random
from .protocol import Websocket

async def connect(uri):
  protocol, address = uri.split("://", 1)
  hostname, *path_parts = address.split('/')
  path = '/' + '/'.join(path_parts)
  hostname, port = (hostname.split(':', 1) + [443 if protocol == 'wss' else 80])[:2]
  
  reader, writer = await asyncio.open_connection(hostname, int(port), ssl=(protocol == 'wss'))
  
  key = binascii.b2a_base64(bytes(random.getrandbits(8) for _ in range(16)))[:-1]
  headers = [
    f'GET {path} HTTP/1.1',
    f'Host: {hostname}:{port}',
    'Connection: Upgrade',
    'Upgrade: websocket', 
    f'Sec-WebSocket-Key: {key.decode()}',
    'Sec-WebSocket-Version: 13',
    f'Origin: http://{hostname}:{port}',
    '', ''
  ]
  
  await writer.awrite('\r\n'.join(headers).encode())
  
  if not (await reader.readline()).startswith(b'HTTP/1.1 101'):
    raise ConnectionError('WebSocket handshake failed')
  
  while await reader.readline() != b'\r\n':
    pass
  
  return Websocket(reader, writer)
