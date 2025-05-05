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
                error_msg(f"[!] Error receiving message: {e}")
    #server response handler
    async def handle_message(self, response: dict):
        response_type = response.get("response_type")
        if response_type == 22 and response.get("username"):  # CONNECT_response
            self.session = response["session"]
            self.username = response["username"]
            self.connected = True
            server_msg(f"[Server] {response['message']}")  
        elif response_type == 23 and not response.get("username"):  # DISCONNECT_response
            self.session = None
            self.connected = False
            server_msg(f"[Server] {response['message']}")  
        elif response_type == 24:  # PING_response
            server_msg("[Server] Pong received.")
        elif response_type == 21:  # OK_response
            server_msg("[Server] OK")
        elif response_type == 20:  # ERROR_response
            error_mesg = response.get("error")
            error_msg(f"[Server] {error_mesg}")
        elif response_type == 36:  # SERVER_MESSAGE
            text = response.get("message")
            server_msg(f"[Server] {text}")
        elif response_type == 37:  # SERVER_SHUTDOWN
            server_msg("[Server] Shutdown notice received. You may reconnect shortly.")
            self.session = None
            self.connected = False
        elif response_type == 32:  # WHOAMI
            server_msg(f"[Server] You are {response.get('username')}.")
        elif response_type == 31:  # WHOIS_response
            username = response.get("username")
            status = response.get("status", "unknown")
            transport = response.get("transport", "unknown")
            channels = response.get("channels", [])
            pubkey = response.get("wireguard_public_key", "")

            server_msg(f"[Server] Username")
            server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY} {username}")
            server_msg(f"[Server] Status")
            if status == "active":
                server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {BRIGHT_GREEN} {status}")
            else:
                server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {BRIGHT_RED} {status}")
            server_msg(f"[Server] Transport")
            server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY} {transport}")
            if channels:
                server_msg(f"[Server] Channels")
                for ch in channels:
                        server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY} {ch}")
            if transport == "wireguard":
                server_msg(f"[Server] Public Key")
                server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY} {pubkey}")
        elif response_type == 34:  # SETUSERNAME
            old = response.get("old_username")
            new = response.get("new_username")
            self.username = new
            server_msg(f"[Server] Username changed: {old} {BRIGHT_MAGENTA}→{GREY} {new}")
        elif response_type == 25:  # CHANNEL_CREATE_response
            channel = response.get("channel")
            desc = response.get("description")
            server_msg(f"[Server] Channel created {BRIGHT_MAGENTA}|{GREY} {channel}: {desc}")
        elif response_type == 28:  # CHANNEL_JOIN_response
            username = response.get("username")
            channel = response.get("channel")
            if not response.get("response_handle"):
                server_msg(f"[Server] {username} joined {channel}")
            else:
                desc = response.get("description")
                server_msg(f"[Server] You joined {BRIGHT_MAGENTA}|{GREY} {channel}: {desc}")
        elif response_type == 26:  # CHANNEL_LIST_response
            channels = response.get("channels", [])
            next_page = response.get("next_page", False)

            if not channels:
                error_msg("[!] No channels found.")
            else:
                server_msg(f"[Server] Channel List ({len(channels)})")
                for ch in channels:
                    server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY} {ch}")
                if next_page:
                    progress_msg("[*] More channels available. Use: /channels <offset>")
        elif response_type == 29:  # CHANNEL_LEFT_response
            username = response.get("username")
            channel = response.get("channel")
            if not response.get("response_handle"):
                server_msg(f"[Server] {username} left {channel}")
            else:
                server_msg(f"[Server] You left {channel}")
        elif response_type == 27:  # CHANNEL_INFO_response
            channel = response.get("channel")
            description = response.get("description", "")
            members = response.get("members", [])

            server_msg(f"[Server] Channel Name")
            server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY}{channel}")
            server_msg(f"[Server] Description")
            server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY}{description}")
            server_msg(f"[Server] Members ({len(members)})")
            for user in members:
                server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY}{user}")
        elif response_type == 35:  # USER_LIST_response
            users = response.get("users", [])
            next_page = response.get("next_page", False)

            if not users:
                error_msg("[!] No users found.")
            else:
                server_msg(f"[Server] User List ({len(users)})")
                for u in users:
                    server_msg(f"[Server]  {BRIGHT_MAGENTA}•  {GREY} {u}")

                if next_page:
                    progress_msg("[*] More users exist. Try: /users <offset>")
        elif response_type == 33:  # USER_MESSAGE_response
            sender = response.get("from_username", "unknown")
            text = response.get("message", "")
            mod_print(f"{GREY}[{current_time()}] [{CYAN}Direct Message{GREY}] {sender} {BRIGHT_RED}➜ {BRIGHT_YELLOW} {text}")
        elif response_type == 30:  # CHANNEL_MESSAGE_response
                sender = response.get("username", "unknown")
                channel = response.get("channel", "?")
                text = response.get("message", "")
                mod_print(f"{GREY}[{current_time()}] [{WHITE}Channel | {channel}{GREY}] {sender} {BRIGHT_RED}➜ {BRIGHT_YELLOW} {text}")
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
                "request_type": 2,
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

    async def whois(self, username: str):
        if self.connected:
            if not username or len(username) > 20:
                error_msg("[!] Invalid username.")
            else:
                request_handle = random.getrandbits(32)
                packet = {
                    "request_type": 10, 
                    "session": self.session,
                    "request_handle": request_handle,
                    "username": username
                }
                self.send(packet)

    async def set_username(self,username):
        if self.connected:
            if ":" in username:
                error_msg("[!] Invalid username. It must not contain ':'.")
            else:
                request_handle = random.getrandbits(32)
                if  SERVER_PORT== 51825: #clear-text port
                    username = f"clear-{username}"
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

    async def join_channel(self, channel: str):
        if self.connected:
            if not channel or len(channel) > 20:
                error_msg("[!] Invalid channel name.")
            else:
                request_handle = random.getrandbits(32)
                packet = {
                    "request_type": 7,  
                    "session": self.session,
                    "request_handle": request_handle,
                    "channel": channel
                }
                self.send(packet)

    async def list_channels(self, offset: int = 0):
        if self.connected:
           request_handle = random.getrandbits(32)
           packet = {
                "request_type": 5,  
                "session": self.session,
                "request_handle": request_handle,
                "offset": offset  # Optional
           }
           self.send(packet)

    async def leave_channel(self, channel: str):
        if self.connected:
            if not channel or len(channel) > 20:
                error_msg("[!] Invalid channel name.")
            else:
                request_handle = random.getrandbits(32)
                packet = {
                    "request_type": 8,  
                    "session": self.session,
                    "request_handle": request_handle,
                    "channel": channel
                }
                self.send(packet)

    async def channel_info(self, channel: str):
        if self.connected:
            if not channel or len(channel) > 20:
                error_msg("[!] Invalid channel name.")
            else:
                request_handle = random.getrandbits(32)
                packet = {
                    "request_type": 6,  
                    "session": self.session,
                    "request_handle": request_handle,
                    "channel": channel
                }
                self.send(packet)

    async def list_users(self, channel: str = "", offset: int = 0):
        if self.connected:
            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 14,  
                "session": self.session,
                "request_handle": request_handle,
                "offset": offset
            }
            if channel:
                if len(channel) > 20:
                    error_msg("[!] Invalid channel name.")
                else:
                    packet["channel"] = channel

            self.send(packet)

    async def send_dm(self, to_username: str, message: str):
        if self.connected:
            if len(to_username) > 20:
                error_msg("[!] Username must be 20 characters or fewer.")
                return
            if len(message) > 500:
                error_msg("[!] Message must be 500 characters or fewer.")
                return

            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 12,
                "session": self.session,
                "request_handle": request_handle,
                "to_username": to_username,
                "message": message
            }
            self.send(packet)

    async def send_channel_msg(self, channel: str, message: str):
        if self.connected:
            if len(channel) > 20:
                error_msg("[!] Channel name must be 20 characters or fewer.")
                return
            if len(message) > 500:
                error_msg("[!] Message must be 500 characters or fewer.")
                return

            request_handle = random.getrandbits(32)
            packet = {
                "request_type": 9,
                "session": self.session,
                "request_handle": request_handle,
                "channel": channel,
                "message": message
            }
            self.send(packet)