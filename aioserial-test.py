import aioserial
import asyncio
from cobs import cobs
import binascii
import struct

class DataReceiver:
    def on_data_received(self, data):
        print("data received")
        pass

class CobsReader:
    def __init__(self, serial, receiver=None):
        self.serial = serial
        self.receiver = receiver
        self.running = True
        self.write_queue = asyncio.Queue()

    def set_receiver(self, receiver):
        self.receiver = receiver

    def write(self, data):
        frame = cobs.encode(data) + bytes([0])
        self.write_queue.put_nowait(frame)

    def close(self):
        self.running = False
        self.serial.close()
        self.write_queue.put_nowait(None)

    def run(self):
        asyncio.create_task(self.reader())
        asyncio.create_task(self.writer())

    async def reader(self):
        print("Reader starting")
        while self.running:
            data = await self.serial.read_until_async(bytes([0]))
            print("Read {} bytes: {}".format(len(data), binascii.hexlify(data)))
            try:
                frame = cobs.decode(data[:-1]) # don't pass trailing zero in
                if self.receiver:
                    if callable(self.receiver):
                        self.receiver(frame)
                    else:
                        self.receiver.on_data_received(data)
            except cobs.DecodeError as e:
                print("Bad COBS frame")
                continue
        print("Reader stopping")

    async def writer(self):
        print("Writer starting")
        while self.running:
            data = await self.write_queue.get()
            if data is None:
                continue
            print("Writing {} bytes: {}".format(len(data), binascii.hexlify(data)))
            await self.serial.write_async(data)
            print("Wrote {} bytes".format(len(data)))
        print("Writer stopping")




async def main():
    s = aioserial.AioSerial('/dev/cu.usbmodem3341731', baudrate=1000000)
    r = CobsReader(s)

    def handler(data):
        i, = struct.unpack_from("<I", data)
        print("Got {}".format(i))
        if i == 100:
            r.close()
            asyncio.get_event_loop().call_soon(lambda: asyncio.get_event_loop().stop())
        else:
            r.write(struct.pack("<I", i + 1))

    r.set_receiver(handler)
    r.run()

    # Kick off
    r.write(struct.pack("<I", 1))

    await asyncio.sleep(1)

try:
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
except KeyboardInterrupt as e:
    # r.close()
    print("EX")
