import asyncio
import socket
import msgpack
import random

SERVER_HOST = 'csc4026z.link'
SERVER_PORT = 51825  #clear text

class ChatClient:
    def __init__(self): #constructor
        self.session = None #session id
        self.username = None #server assigned username
        self.connected = False

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.server_addr = (SERVER_HOST, SERVER_PORT)

    def send(self, message: dict):
        packed = msgpack.packb(message)
        self.sock.sendto(packed, self.server_addr)

    async def connect(self):
        print("[*] Sending CONNECT request...")
        request_handle = random.getrandbits(32)
        packet = {
            "request_type": 1,
            "request_handle": request_handle
        }
        self.send(packet)

        try:
            data, _ = await asyncio.get_event_loop().sock_recvfrom(self.sock, 1460)
            response = msgpack.unpackb(data)
            if response.get("response_type") == 22:  # CONNECT_response
                self.session = response["session"]
                self.username = response["username"]
                self.connected = True
                print(f"[+] Connected successfully! Assigned username: {self.username}")
            else:
                print("[!] Unexpected response:", response)
        except Exception as e:
            print("[!] Failed to connect:", e)