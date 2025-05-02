import asyncio
import os
from chat_client import ChatClient

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear') 
    
def print_menu():
    print("\nAvailable commands:")

    print("\n[Session Management]")
    print("  /connect                      - Connect to the chat server")
    print("  /whoami                       - Show your current username")
    print("  /setname <new_username>       - Change your username")
    print("  /quit                         - Disconnect and exit")

    print("\n[Channel Commands]")
    print("  /channels                     - List all available channels")
    print("  /join <channel>               - Join a channel")
    print("  /leave <channel>              - Leave a channel")
    print("  /create <channel> <desc>      - Create a new channel with description")
    print("  /info <channel>               - Show info about a channel (desc, members)")
    print("  /msg <channel> <message>      - Send a message to a channel")

    print("\n[User Commands]")
    print("  /users                        - List all users")
    print("  /users <channel>              - List users in a specific channel")
    print("  /whois <username>             - Get details about a user")
    print("  /dm <username> <message>      - Send a private message (DM) to a user")

    print()

async def prompt_loop(client: ChatClient):
    print_menu()  # Show options on startup

    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
        user_input = user_input.strip()

        if not client.connect:
            break
        if user_input == "/connect":
            if client.connected:
                print("[!] Already connected.")
            else:
                await client.connect()
                if client.connected:
                    asyncio.create_task(client.receive_loop())
                    asyncio.create_task(client.ping())
                    print_menu()  # Show commands again after successful connect

        elif user_input == "/quit":
            await client.disconnect()
        else:
            print("[!] Unknown command.")
            print_menu()

async def main():
    client = ChatClient()
    await prompt_loop(client) #cli options

if __name__ == "__main__":
    asyncio.run(main())