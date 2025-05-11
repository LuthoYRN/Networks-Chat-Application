import os
import socket
import struct
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

# Import functions from Task01_keygeneration.py
from KeyGeneration import *

SERVER_HOST = "csc4026z.link"
SERVER_PORT = 51820

def perform_handshake(sock):
    print("[+] Starting WireGuard handshake process...")
    
    # ======== TASK 2: INITIAL HANDSHAKE ========
    # Generate a random sender index
    sender_index = os.urandom(4)
    msg_type = struct.pack("<B", 1)  # Type 1 for initial handshake
    reserved = b"\x00" * 3
    
    # Initialize the handshake hash with protocol name
    chaining_key = blake2s(CONSTRUCTION)
    hash_ = blake2s(blake2s(chaining_key + IDENTIFIER) + server_static_public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ))
    
    # Update with ephemeral key
    hash_ = blake2s(hash_ + ephemeral_public_bytes)
    temp_k1 = hmac_hash(chaining_key, ephemeral_public_bytes)
    chaining_key = hmac_hash(temp_k1, b"\x01")
    
    # First DH: our ephemeral private key and server's static public key
    ss1 = ephemeral_private.exchange(server_static_public)
    temp = hmac_hash(chaining_key, ss1)
    chaining_key = hmac_hash(temp, b"\x01")
    key1 = hmac_hash(temp, chaining_key + b"\x02")
    
    # Encrypt our static public key
    encrypted_static = aead_encrypt(key1, 0, client_static_public_bytes, hash_)
    hash_ = blake2s(hash_ + encrypted_static)
    
    # Second DH: our static private key and server's static public key
    ss2 = client_static_private.exchange(server_static_public)
    temp2 = hmac_hash(chaining_key, ss2)
    chaining_key = hmac_hash(temp2, b"\x01")
    key2 = hmac_hash(temp2, chaining_key + b"\x02")
    
    # Encrypt timestamp
    timestamp = tai64n_timestamp()
    encrypted_timestamp = aead_encrypt(key2, 0, timestamp, hash_)
    hash_ = blake2s(hash_ + encrypted_timestamp)
    
    # Calculate MAC for the handshake packet
    mac1_key = blake2s(LABEL_MAC1 + server_static_public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ))
    mac1 = hmac_hash(mac1_key, msg_type + reserved + sender_index + ephemeral_public_bytes + 
                     encrypted_static + encrypted_timestamp)[:16]
    mac2 = b"\x00" * 16
    
    # Construct the complete handshake packet
    handshake_packet = (
        msg_type + reserved + sender_index + ephemeral_public_bytes +
        encrypted_static + encrypted_timestamp + mac1 + mac2
    )
    
    print(f"[+] Sending handshake packet ({len(handshake_packet)} bytes)...")
    
    # Send handshake and receive response
    sock.settimeout(5)
    
    try:
        sock.sendto(handshake_packet, (SERVER_HOST, SERVER_PORT))
        response, _ = sock.recvfrom(1024)
        print(f"[+] Received handshake response: {len(response)} bytes")
        print("[+] Response: ", response.hex())
                    
    except socket.timeout:
        print("[-] Timeout: No response received from server.")
        return None, None
    except Exception as e:
        print(f"[-] Error during handshake: {e}")
        return None, None