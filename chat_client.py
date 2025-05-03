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
            server_msg(f"[Server] {error_msg}")
        elif response_type == 36:  # SERVER_MESSAGE
            text = response.get("message")
            server_msg(f"[Broadcast] {text}")
        elif response_type == 37:  # SERVER_SHUTDOWN
            server_msg("[Server] Shutdown notice received. You may reconnect shortly.")
            self.session = None
            self.connected = False
        elif response_type == 32:  # WHOAMI
            server_msg(f"[Server] You are {response.get('username')}.")
        elif response_type == 31:  # WHOIS
            server_msg(f"[Server] Information: username: {response.get('username')} , status: {response['status']}, transport: {response['transport']}.") 
        elif response_type == 34:  # SETUSERNAME
            old = response.get("old_username")
            new = response.get("new_username")
            self.username = new
            server_msg(f"[Server] Username changed: {old} → {new}")
        elif response_type == 25:  # CHANNEL_CREATE_response
            channel = response.get("channel")
            desc = response.get("description")
            server_msg(f"[Server] Channel created | {channel}: {desc}")
    #protocol functions
    async def connect(self):
        progress_msg("[*] Sending CONNECT request...")
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
            error_msg(f"[!] Failed to connect: {e}")

    async def disconnect(self):
        if self.connected:
            progress_msg("[*] Sending DISCONNECT request...")
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
    
    async def whois(self,username):
        if self.connected:
            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 10,
                "session": self.session,
                "request_handle": request_handle,
                "username":username
            }
            self.send(packet)
    
    async def set_username(self,username):
        if self.connected:
            if not username.startswith("clear-"):
                error_msg("[!] Invalid username. It must start with 'clear-'.")
            elif ":" in username:
                error_msg("[!] Invalid username. It must not contain ':'.")
            else:
                request_handle = random.getrandbits(32)
                packet = {
                    "request_type": 13,
                    "session": self.session,
                    "request_handle": request_handle,
                    "username":username
                }
                self.send(packet)

    async def create_channel(self,name:str,description:str):
        if self.connected:
            if not name or len(name) > 20:
                error_msg("[!] Channel name must be 1–20 characters.")
            elif len(description) > 100:
                error_msg("[!] Description too long (max 100 characters).")
            else:
                request_handle = random.getrandbits(32)
                packet = {
                    "request_type": 4,
                    "session": self.session,
                    "request_handle": request_handle,
                    "channel":name,
                    "description":description
                }
                self.send(packet)