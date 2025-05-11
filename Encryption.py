import os
import struct
from utility import *
from KeyGeneration import *
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

class Encryption:
    def __init__(self):
        self.session_established = False
        self.sender_index = os.urandom(4)  # 4 random bytes for sender index
        self.receiver_index = None
        self.sending_key = None
        self.receiving_key = None
        self.sending_counter = 0
        self.receiving_counter = 0
        
        # For handshake state
        self.hash = None
        self.chaining_key = None
    
    def create_handshake_initiation(self):
        """Create a WireGuard handshake initiation message"""
        msg_type = struct.pack("<B", 1)  # Type 1 for initial handshake
        reserved = b"\x00" * 3
        
        # Initialize the handshake hash with protocol name
        self.chaining_key = blake2s(CONSTRUCTION)
        self.hash = blake2s(blake2s(self.chaining_key + IDENTIFIER) + server_static_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ))
        
        # Update with ephemeral key
        self.hash = blake2s(self.hash + ephemeral_public_bytes)
        temp_k1 = hmac_hash(self.chaining_key, ephemeral_public_bytes)
        self.chaining_key = hmac_hash(temp_k1, b"\x01")
        
        # First DH: our ephemeral private key and server's static public key
        ss1 = ephemeral_private.exchange(server_static_public)
        temp = hmac_hash(self.chaining_key, ss1)
        self.chaining_key = hmac_hash(temp, b"\x01")
        key1 = hmac_hash(temp, self.chaining_key + b"\x02")
        
        # Encrypt our static public key
        encrypted_static = aead_encrypt(key1, 0, client_static_public_bytes, self.hash)
        self.hash = blake2s(self.hash + encrypted_static)
        
        # Second DH: our static private key and server's static public key
        ss2 = client_static_private.exchange(server_static_public)
        temp2 = hmac_hash(self.chaining_key, ss2)
        self.chaining_key = hmac_hash(temp2, b"\x01")
        key2 = hmac_hash(temp2, self.chaining_key + b"\x02")
        
        # Encrypt timestamp
        timestamp = tai64n_timestamp()
        encrypted_timestamp = aead_encrypt(key2, 0, timestamp, self.hash)
        self.hash = blake2s(self.hash + encrypted_timestamp)
        
        # Calculate MAC for the handshake packet
        mac1_key = blake2s(LABEL_MAC1 + server_static_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ))
        mac1 = hmac_hash(mac1_key, msg_type + reserved + self.sender_index + ephemeral_public_bytes + 
                        encrypted_static + encrypted_timestamp)[:16]
        # mac2 is all zeros per the simplified spec
        mac2 = b"\x00" * 16
        
        # Construct the complete handshake packet
        handshake_packet = (
            msg_type + reserved + self.sender_index + ephemeral_public_bytes +
            encrypted_static + encrypted_timestamp + mac1 + mac2
        )
        
        return handshake_packet
    
    def process_handshake_response(self, response):
        """Process a WireGuard handshake response message"""
        if len(response) < 92:  # Minimum expected size for a handshake response
            error_msg("[!] Response too short")
            return False
            
        # Extract message fields
        msg_type = response[0]
        if msg_type != 2:  # Type 2 for handshake response
            error_msg(f"[!] Unexpected message type: {msg_type}")
            return False
            
        # Extract indices
        response_sender_index = response[4:8]
        response_receiver_index = response[8:12]
                
        # Check if the receiver index in the response matches our sender index
        if response_receiver_index != self.sender_index:
            error_msg("[!] Warning: Receiver index mismatch")
        
        # The server's sender index becomes our receiver index for transport data
        self.receiver_index = response_sender_index

        # Extract necessary fields
        responder_ephemeral = response[12:44]  # Server's ephemeral public key
        encrypted_empty = response[44:60]  # Encrypted empty message
        # Update handshake state
        self.hash = blake2s(self.hash + responder_ephemeral)
        temp = hmac_hash(self.chaining_key, responder_ephemeral)
        self.chaining_key = hmac_hash(temp, b"\x01")
        
        # Perform DH operation: our ephemeral private with responder's ephemeral public
        dh1 = ephemeral_private.exchange(x25519.X25519PublicKey.from_public_bytes(responder_ephemeral))
        temp = hmac_hash(self.chaining_key, dh1)
        self.chaining_key = hmac_hash(temp, b"\x01")
        
        # Perform DH operation: our static private with responder's ephemeral public
        dh2 = client_static_private.exchange(x25519.X25519PublicKey.from_public_bytes(responder_ephemeral))
        temp = hmac_hash(self.chaining_key, dh2)
        self.chaining_key = hmac_hash(temp, b"\x01")
        
        zero_psk = b"\x00" * 32
        temp = hmac_hash(self.chaining_key, zero_psk)
        self.chaining_key = hmac_hash(temp, b"\x01")
        temp2 = hmac_hash(temp, self.chaining_key + b"\x02")
        key = hmac_hash(temp, temp2 + b"\x03")
        self.hash = blake2s(self.hash + temp2)
        
        # Decrypt the empty message
        try:
            empty = aead_decrypt(key, 0, encrypted_empty, self.hash)
            if empty != b'':
                error_msg("[!] Decrypted empty is not empty")
                return False
        except Exception as e:
            error_msg(f"[!] Error decrypting empty message: {e}")
            return False
            
        self.hash = blake2s(self.hash + encrypted_empty)
        
        # Derive transport keys 
        temp = hmac_hash(self.chaining_key, b'')
        self.sending_key = hmac_hash(temp, b"\x01")
        self.receiving_key = hmac_hash(temp, self.sending_key + b"\x02")
        self.sending_counter = 0
        self.receiving_counter = 0
        
        self.session_established = True
        return True
    
    def encrypt_data(self, data):
        """Encrypt data for transport"""
        if not self.session_established:
            raise Exception("Session not established")
        
        # Create message header
        msg_type = struct.pack("<B", 4)  # Type 4 for transport data
        reserved = b"\x00" * 3
        counter = struct.pack("<Q", self.sending_counter)
            
        # Encrypt the data
        encrypted = aead_encrypt(self.sending_key, self.sending_counter, data, b'')
        
        # Construct the complete message
        message = msg_type + reserved + self.receiver_index + counter + encrypted
        
        # Increment counter
        self.sending_counter += 1
        
        return message

    def decrypt_data(self, data):
        """Decrypt transport data"""
        if not self.session_established:
            raise Exception("Session not established")
            
        if len(data) < 16:  # Header size
            error_msg("[!] Data too short")
            return None
            
        # Extract header fields
        msg_type = data[0]
        if msg_type != 4:  # Type 4 for transport data
            error_msg(f"[!] Unexpected message type: {msg_type}")
            return None
            
        # Check receiver index matches our sender index
        receiver_index = data[4:8]
        if receiver_index != self.sender_index:
            error_msg("[!] Receiver index mismatch")
            return None
            
        # Extract counter and encrypted data
        counter_bytes = data[8:16]
        counter = struct.unpack("<Q", counter_bytes)[0]
        encrypted = data[16:]
        
        if counter < self.receiving_counter:
            error_msg(f"[!] Possible replay attack: counter {counter} < {self.receiving_counter}")
            return None
            
        # Decrypt the data
        try:
            decrypted = aead_decrypt(self.receiving_key, counter, encrypted, b'')
            # Update counter
            if counter >= self.receiving_counter:
                self.receiving_counter = counter + 1
            return decrypted
        except Exception as e:
            error_msg(f"[!] Error decrypting data: {e}")
            return None