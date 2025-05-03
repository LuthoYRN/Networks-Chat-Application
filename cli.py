import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from chat_client import ChatClient
from utility import *

custom_style = Style.from_dict({
    "prompt": "ansiyellow",
    "": "ansiyellow",  # Apply yellow to user input text
})   

def print_menu(connected):
    status = ""
    if connected:
        status = BRIGHT_GREEN+"CONNECTED"+RESET
    else:
        status = BRIGHT_RED+"DISCONNECTED"+RESET
    mod_print(f"{RESET}\nAvailable commands: {status}")

    if connected:
        print("\n[Session Management]")
        mod_print(f"  /whoami                       {BRIGHT_YELLOW}- Show your current username{RESET}")
        mod_print(f"  /setname <new_username>       {BRIGHT_YELLOW}- Change your username{RESET}")
        mod_print(f"  /quit                         {BRIGHT_YELLOW}- Disconnect and exit{RESET}")

        print("\n[Channel Commands]")
        mod_print(f"  /channels                     {BRIGHT_YELLOW}- List all available channels{RESET}")
        mod_print(f"  /join <channel>               {BRIGHT_YELLOW}- Join a channel{RESET}")
        mod_print(f"  /leave <channel>              {BRIGHT_YELLOW}- Leave a channel{RESET}")
        mod_print(f"  /create <channel> <desc>      {BRIGHT_YELLOW}- Create a new channel with description{RESET}")
        mod_print(f"  /info <channel>               {BRIGHT_YELLOW}- Show info about a channel (desc, members){RESET}")
        mod_print(f"  /msg <channel> <message>     {BRIGHT_YELLOW} - Send a message to a channel{RESET}")

        print("\n[User Commands]")
        mod_print(f"  /users                        {BRIGHT_YELLOW}- List all users{RESET}")
        mod_print(f"  /users <channel>             {BRIGHT_YELLOW} - List users in a specific channel{RESET}")
        mod_print(f"  /whois <username>            {BRIGHT_YELLOW} - Get details about a user{RESET}")
        mod_print(f"  /dm <username> <message>     {BRIGHT_YELLOW} - Send a private message (DM) to a user{RESET}")
       
        print("\n[Other]")
        mod_print(f"  /clear                        {BRIGHT_YELLOW}- clear interface{RESET}")
    
    else:
        print("\n[Session Management]")
        mod_print(f"  /connect                     {BRIGHT_YELLOW} - Connect to the chat server{RESET}")
        mod_print(f"  /quit                        {BRIGHT_YELLOW} - exit{RESET}")
        
        print("\n[Other]")
        mod_print(f"  /clear                       {BRIGHT_YELLOW} - clear interface{RESET}")
    print()

async def prompt_loop(client: ChatClient):
    session = PromptSession()
    typewriter_effect(CHAT_HEADER, delay=0.05)
    print_menu(client.connected)  # Show options on startup
    with patch_stdout():
            while True:
                try:
                    user_input = await session.prompt_async("> ",style=custom_style)
                    user_input = user_input.strip()
                    #process commands
                    if user_input == "/connect":
                        if client.connected:
                            mod_print(f"{BRIGHT_RED}[!] Already connected.{RESET}")
                        else:
                            await client.connect()
                            if client.connected:
                                asyncio.create_task(client.receive_loop())
                                asyncio.create_task(client.ping())
                                print_menu(client.connected)
                    elif user_input == "/clear":
                        clear_terminal()
                        print_menu(client.connected)
                    elif user_input == "/quit":
                        mod_print(RESET)
                        break
                    else:
                        mod_print(f"{BRIGHT_RED}[!] Unknown command.{RESET}")
                except KeyboardInterrupt:
                    # Handle Ctrl+C
                    break
                except EOFError:
                    # Handle Ctrl+D
                    break

async def main():
    client = ChatClient()
    await prompt_loop(client) #cli options

if __name__ == "__main__":
    asyncio.run(main())