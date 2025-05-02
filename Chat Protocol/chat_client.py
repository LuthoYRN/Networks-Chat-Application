import asyncio
import socket
import msgpack
import random

SERVER_HOST = 'csc4026z.link'
SERVER_PORT = 51825  #clear text
def safe_print(message):
    print(f"\r{message}\n> ", end="", flush=True)

class ChatClient:
    def __init__(self): #constructor
        self.session = None #session id
        self.username = None #server assigned username
        self.connected = False
        self.byte_limit = 1460

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.server_addr = (SERVER_HOST, SERVER_PORT)

    def send(self, message: dict):
        packed = msgpack.packb(message)
        self.sock.sendto(packed, self.server_addr)
    
    #receive loop
    async def receive_loop(self):
        while True:
            try:
                data, _ = await asyncio.get_event_loop().sock_recvfrom(self.sock, self.byte_limit)
                message = msgpack.unpackb(data)
                await self.handle_message(message)
            except Exception as e:
                safe_print("[!] Error receiving message:", e)
    
    async def handle_message(self, response: dict):
        response_type = response.get("response_type")
        if response_type == 22 and response.get("username"):  # CONNECT_response
            self.session = response["session"]
            self.username = response["username"]
            self.connected = True
            print(f"[+] Connected successfully! Assigned username: {self.username}")
            message = response["message"]
            print(f"[Server] {message}")  
        elif response_type == 22 and not response.get("username"):  # DISCONNECT_response
            self.session = None
            self.connected = False
            message = response["message"]
            safe_print("[Server]",message)
        elif response_type == 24:  # PING response
            safe_print("[Server] Pong received.")
        elif response_type == 21:  # OK
            safe_print("[Server] OK")
        elif response_type == 20:  # ERROR
            error_msg = response.get("error")
            safe_print(f"[Server ERROR] {error_msg}")
        elif response_type == 36:  # SERVER_MESSAGE
            text = response.get("message")
            safe_print(f"[Broadcast] {text}")
        elif response_type == 37:  # SERVER_SHUTDOWN
            safe_print("[Server] Shutdown notice received. You may reconnect shortly.")
            self.session = None
            self.connected = False
        else:
            safe_print("[Server] Unhandled message:", message)

    #protocol functions
    async def connect(self):
        print("[*] Sending CONNECT request...")
        request_handle = random.getrandbits(32)
        packet = {
            "request_type": 1,
            "request_handle": request_handle
        }
        self.send(packet)
        try:
            data, _ = await asyncio.get_event_loop().sock_recvfrom(self.sock, self.byte_limit)
            response = msgpack.unpackb(data)        
            await self.handle_message(response)
        except Exception as e:
            print("[!] Failed to connect:", e)

    async def disconnect(self):
        print("[*] Sending DISCONNECT request...")
        request_handle = random.getrandbits(32)
        packet = {
            "request_type": 23,
            "session":self.session,
            "request_handle": request_handle
        }
        self.send(packet)

    async def ping(self):
        while self.connected:
            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 3,
                "session":self.session,
                "request_handle": request_handle
            }
            self.send(packet)
            await asyncio.sleep(20)
