import os
import socket
import struct
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

# Import functions from Task01_keygeneration.py
from Task01_keygeneration import *

SERVER_HOST = "csc4026z.link"
SERVER_PORT = 51820

def perform_handshake(sender_index):
    print("[+] Starting WireGuard handshake process...")
    
    # ======== TASK 2: INITIAL HANDSHAKE ========
    # Generate a random sender index
    # sender_index = os.urandom(4)
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    
    try:
        sock.sendto(handshake_packet, (SERVER_HOST, SERVER_PORT))
        response, _ = sock.recvfrom(1024)
        print(f"[+] Received handshake response: {len(response)} bytes")
        print("[+] Response: ", response.hex())
        
        # ======== TASK 3: PROCESS RESPONSE ========
        # Parse the response packet
        if len(response) < 56:  # Basic sanity check
            print("[-] Response packet too short")
            return None, None
        
        msg_type = response[0]
        if msg_type != 2:  # Handshake response should be type 2
            print(f"[-] Unexpected message type: {msg_type}")
            return None, None
        
        responder_sender_index = response[4:8]
        responder_receiver_index = response[8:12]  # This should match our sender_index
        responder_ephemeral = response[12:44]  # 32 bytes for ephemeral key
        
        # Extract the encrypted data (the rest of the packet minus MACs)
        encrypted_nothing = response[44:-32]  # Empty in WireGuard response
        mac1 = response[-32:-16]
        mac2 = response[-16:]
        
        print(f"[+] Responder's ephemeral public key: {responder_ephemeral.hex()[:16]}...")
        
        # Validate the receiver index
        if responder_receiver_index != sender_index:
            print("[-] Receiver index in response doesn't match our sender index")
            print(f"Expected: {sender_index.hex()}, Got: {responder_receiver_index.hex()}")
            return None, None
        
        # Update the handshake hash with the responder's ephemeral key
        hash_ = blake2s(hash_ + responder_ephemeral)
        
        # Convert responder's ephemeral to a key object
        responder_ephemeral_key = x25519.X25519PublicKey.from_public_bytes(responder_ephemeral)
        
        # Third DH: our ephemeral private key and responder's ephemeral public key
        ss3 = ephemeral_private.exchange(responder_ephemeral_key)
        temp3 = hmac_hash(chaining_key, ss3)
        chaining_key = hmac_hash(temp3, b"\x01")
        
        # ======== TASK 4: DERIVE FINAL SESSION KEYS ========
        # Derive the final transport keys using KDF3
        print("[+] Deriving final session keys...")
        key_send, key_recv, key_confirm = kdf3(chaining_key, b"")
        
        # These are the actual symmetric keys used for the secure session:
        # - key_send (T_I_send): Used to encrypt data we send to the server
        # - key_recv (T_I_recv): Used to decrypt data we receive from the server
        print(f"[+] Derived send key (T_I_send): {key_send.hex()[:16]}...")
        print(f"[+] Derived recv key (T_I_recv): {key_recv.hex()[:16]}...")
        
        # Wait for encrypted data message
        try:
            print("[+] Waiting for encrypted message...")
            encrypted_message, _ = sock.recvfrom(1024)
            
            # Parse the encrypted message
            if len(encrypted_message) < 16:  # Basic check
                print("[-] Encrypted message too short")
            else:
                msg_type = encrypted_message[0]
                if msg_type != 4:  # Data packets are type 4
                    print(f"[-] Unexpected message type for data: {msg_type}")
                else:
                    receiver_idx = encrypted_message[4:8]
                    counter = struct.unpack("<Q", encrypted_message[8:16])[0]
                    encrypted_payload = encrypted_message[16:]
                    
                    print(f"[+] Received data packet with counter: {counter}")
                    
                    # Decrypt the payload
                    try:
                        decrypted = aead_decrypt(key_recv, counter, encrypted_payload, encrypted_message[:16])
                        print(f"[+] Decrypted message: {decrypted.decode('utf-8')}")
                    except Exception as e:
                        print(f"[-] Failed to decrypt message: {e}")
                        
        except socket.timeout:
            print("[!] No encrypted message received after handshake")
        
        return key_send, key_recv
        
    except socket.timeout:
        print("[-] Timeout: No response received from server.")
        return None, None
    except Exception as e:
        print(f"[-] Error during handshake: {e}")
        return None, None
    finally:
        sock.close()

# ======== TASK 4: DERIVE FINAL SESSION KEYS ========
def kdf3(chaining_key, input_material):
    """
    Key derivation function that generates three outputs from a chaining key and input material.
    
    This is a crucial part of the WireGuard protocol - it derives the final symmetric
    encryption keys from the shared secrets established during the handshake.
    
    Returns:
        - key_send (T_I_send): Used to encrypt messages we send to the server
        - key_recv (T_I_recv): Used to decrypt messages we receive from the server  
        - key_confirm: An additional key which may be used for session confirmation
    """
    temp1 = hmac_hash(chaining_key, input_material + b"\x01")  # T_I_send
    temp2 = hmac_hash(chaining_key, temp1 + input_material + b"\x02")  # T_I_recv
    temp3 = hmac_hash(chaining_key, temp2 + input_material + b"\x03")  # Confirmation key
    return temp1, temp2, temp3

def send_encrypted_message(key_send, message, counter, sender_index):
    """
    Encrypts and sends a chat message in a WireGuard transport packet.
    
    Args:
        key_send (bytes): The T_I_send session key.
        message (str): The plaintext chat message to send.
        counter (int): The current message counter (nonce).
        sender_index (bytes): Sender's index (4 bytes, generated during handshake).
    """
    msg_type = struct.pack("<B", 4)  # Type 4 for transport data
    reserved = b"\x00" * 3
    counter_bytes = struct.pack("<Q", counter)
    
    # Encrypt the chat message using AEAD
    encrypted_payload = aead_encrypt(key_send, counter, message, msg_type + reserved + sender_index + counter_bytes)
    
    # Construct full transport packet
    transport_packet = msg_type + reserved + sender_index + counter_bytes + encrypted_payload
    
    # Send packet to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(transport_packet, (SERVER_HOST, SERVER_PORT))
    print(f"[+] Sent encrypted chat message: '{message}' with counter {counter}")
    sock.close()

def receive_encrypted_message(key_recv):
    """
    Listens for a WireGuard transport message and decrypts it using T_I_recv.
    
    Args:
        key_recv (bytes): The T_I_recv session key.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', SERVER_PORT))
    sock.settimeout(10)

    try:
        print("[+] Listening for incoming encrypted chat message...")
        packet, addr = sock.recvfrom(4096)

        if len(packet) < 16:
            print("[-] Received packet too short to be valid.")
            return

        msg_type = packet[0]
        if msg_type != 4:
            print(f"[-] Unexpected message type: {msg_type}")
            return

        receiver_index = packet[4:8]
        counter = struct.unpack("<Q", packet[8:16])[0]
        encrypted_data = packet[16:]

        aad = packet[:16]  # Associated data for AEAD: msg_type + reserved + receiver_index + counter
        try:
            plaintext = aead_decrypt(key_recv, counter, encrypted_data, aad)
            print(f"[+] Received decrypted chat message: {plaintext.decode('utf-8')}")
        except Exception as e:
            print(f"[-] Failed to decrypt incoming message: {e}")

    except socket.timeout:
        print("[!] Timeout: No message received.")
    finally:
        sock.close()



if __name__ == "__main__":
    # Perform the handshake and get the derived keys
    key_send, key_recv = perform_handshake()
    
    if key_send and key_recv:
        print("[+] Handshake completed successfully!")
        
        # Optionally send a test message
        # You would need the responder_index from the handshake response
        # send_encrypted_message(key_send, "Hello, server!", 0, responder_index)
    else:
        print("[-] Handshake failed.")