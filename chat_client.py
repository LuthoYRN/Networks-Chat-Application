import asyncio
import socket
import msgpack
import random
from utility import *

SERVER_HOST = 'csc4026z.link'
SERVER_PORT = 51825  #clear text

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
                server_msg(f"[!] Error receiving message: {e}")
    #server response handler
    async def handle_message(self, response: dict):
        response_type = response.get("response_type")
        if response_type == 22 and response.get("username"):  # CONNECT_response
            self.session = response["session"]
            self.username = response["username"]
            self.connected = True
            server_msg(f"[Server] {response['message']}")  
        elif response_type == 22 and not response.get("username"):  # DISCONNECT_response
            self.session = None
            self.connected = False
            server_msg(f"[Server] {response['message']}")  
        elif response_type == 24:  # PING response
            server_msg("[Server] Pong received.")
        elif response_type == 21:  # OK
            server_msg("[Server] OK")
        elif response_type == 20:  # ERROR
            error_msg = response.get("error")
            server_msg(f"[Server ERROR] {error_msg}")
        elif response_type == 36:  # SERVER_MESSAGE
            text = response.get("message")
            server_msg(f"[Broadcast] {text}")
        elif response_type == 37:  # SERVER_SHUTDOWN
            server_msg("[Server] Shutdown notice received. You may reconnect shortly.")
            self.session = None
            self.connected = False
        elif response_type == 32:  # WHOAMI
            server_msg(f"[Server] You are {response.get('username')}.")
        elif response_type == 34:  # SETUSERNAME
            old = response.get("old_username")
            new = response.get("new_username")
            self.username = new
            server_msg(f"[Server] Username changed: {old} → {new}")
    #protocol functions
    async def connect(self):
        server_msg("[*] Sending CONNECT request...")
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
            server_msg(f"[!] Failed to connect: {e}")

    async def disconnect(self):
        if self.connected:
            server_msg("[*] Sending DISCONNECT request...")
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

    async def whoami(self):
        if self.connected:
            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 11,
                "session": self.session,
                "request_handle": request_handle
            }
            self.send(packet)
            
    async def set_username(self,username):
        if self.connected:
            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 13,
                "session": self.session,
                "request_handle": request_handle,
                "username":username
            }
            self.send(packet)

def server_msg(message):
    mod_print(f"{GREY}{message}{RESET}")