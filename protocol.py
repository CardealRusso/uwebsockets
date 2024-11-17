import asyncio, random, struct, re

OP_CONT = const(0x0)
OP_TEXT = const(0x1)
OP_BYTES = const(0x2)
OP_CLOSE = const(0x8)
OP_PING = const(0x9)
OP_PONG = const(0xa)

MAX_PAYLOAD = 125

class Websocket:
  def __init__(self, reader, writer):
    self.reader = reader
    self.writer = writer
    self.open = True
    self.message_buffer = []
    self.message_opcode = None

  async def read_frame(self):
    byte1, byte2 = struct.unpack('!BB', await self.reader.read(2))
    
    fin = bool(byte1 & 0x80)
    opcode = byte1 & 0x0f
    mask = bool(byte2 & (1 << 7))
    length = byte2 & 0x7f
    
    if length == 126:
      length, = struct.unpack('!H', await self.reader.read(2))
    elif length == 127:
      length, = struct.unpack('!Q', await self.reader.read(8))
      
    if mask:
      mask_bits = await self.reader.read(4)
      
    data = await self.reader.read(length)
    if mask:
      data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))
      
    return fin, opcode, data

  async def write_frame(self, opcode, data=b'', fin=True):
    byte1 = (0x80 if fin else 0x00) | opcode
    byte2 = 0x80
    length = len(data)
    
    if length <= 125:
      await self.writer.awrite(struct.pack('!BB', byte1, byte2 | length))
    elif length < (1 << 16):
      await self.writer.awrite(struct.pack('!BBH', byte1, byte2 | 126, length))
    else:
      await self.writer.awrite(struct.pack('!BBQ', byte1, byte2 | 127, length))
      
    mask_bits = struct.pack('!I', random.getrandbits(32))
    await self.writer.awrite(mask_bits)
    data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))
    await self.writer.awrite(data)

  async def recv(self):
    while self.open:
      try:
        fin, opcode, data = await self.read_frame()
        
        if opcode == OP_CLOSE:
          self.open = False
          await self.writer.aclose()
          await self.reader.aclose()
          return None
          
        if opcode == OP_PING:
          await self.write_frame(OP_PONG, data)
          continue
          
        if opcode == OP_PONG:
          continue

        if opcode == OP_CONT:
          if not self.message_buffer:
            raise ValueError("Continuation frame without start frame")
          self.message_buffer.append(data)
        else:
          self.message_buffer = [data]
          self.message_opcode = opcode

        if fin:
          data = b''.join(self.message_buffer)
          opcode = self.message_opcode
          self.message_buffer = []
          self.message_opcode = None
          
          return data.decode() if opcode == OP_TEXT else data
          
      except Exception as ex:
        self.open = False
        await self.writer.aclose()
        await self.reader.aclose()
        return None
  
  async def send(self, data):
    if not self.open:
      return
      
    try:
      if isinstance(data, str):
        data = data.encode()
        opcode = OP_TEXT
      else:
        opcode = OP_BYTES
      
      for i in range(0, len(data), MAX_PAYLOAD):
        chunk = data[i:i + MAX_PAYLOAD]
        is_first = i == 0
        is_last = i + MAX_PAYLOAD >= len(data)
        
        frame_opcode = opcode if is_first else OP_CONT
        await self.write_frame(frame_opcode, chunk, fin=is_last)
        
    except Exception as ex:
      self.open = False
      await self.writer.aclose()
      await self.reader.aclose()
