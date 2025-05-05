import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from chat_client import ChatClient
from utility import *
from shutil import get_terminal_size

custom_style = Style.from_dict({
    "prompt": "ansiyellow",
    "": "ansiyellow",  # Apply yellow to user input text,
    "bottom-toolbar": "bg:#000000 fg:#aaaaaa",  
    "bottom-toolbar.text": "bg:#000000 fg:#aaaaaa",
})   

def print_menu(connected):
    status = ""
    if connected:
        status = f"{BRIGHT_GREEN}•{RESET}"
    else:
        status =  f"{BRIGHT_RED}•{RESET}"

    mod_print(f"{RESET}\nAvailable commands: {status}")
    mod_print("\n[Session Management]")   
    if connected:
        mod_print(f"  /whoami                       {BRIGHT_YELLOW}- Show your current username{RESET}")
        mod_print(f"  /setname <new_username>       {BRIGHT_YELLOW}- Change your username{RESET}")
        mod_print(f"  /quit                         {BRIGHT_YELLOW}- Disconnect and exit{RESET}")
        mod_print("\n[Channel Commands]")
        mod_print(f"  /channels                     {BRIGHT_YELLOW}- List all available channels{RESET}")
        mod_print(f"  /join <channel>               {BRIGHT_YELLOW}- Join a channel{RESET}")
        mod_print(f"  /leave <channel>              {BRIGHT_YELLOW}- Leave a channel{RESET}")
        mod_print(f"  /create <channel> <desc>      {BRIGHT_YELLOW}- Create a new channel with description{RESET}")
        mod_print(f"  /info <channel>               {BRIGHT_YELLOW}- Show info about a channel (desc, members){RESET}")
        mod_print(f"  /msg <channel> <message>     {BRIGHT_YELLOW} - Send a message to a channel{RESET}")
        mod_print("\n[User Commands]")
        mod_print(f"  /users                        {BRIGHT_YELLOW}- List all users{RESET}")
        mod_print(f"  /users <channel>             {BRIGHT_YELLOW} - List users in a specific channel{RESET}")
        mod_print(f"  /whois <username>            {BRIGHT_YELLOW} - Get details about a user{RESET}")
        mod_print(f"  /dm <username> <message>     {BRIGHT_YELLOW} - Send a private message (DM) to a user{RESET}")   
    else:
        mod_print(f"  /connect                     {BRIGHT_YELLOW} - Connect to the chat server{RESET}")
        mod_print(f"  /quit                        {BRIGHT_YELLOW} - exit{RESET}")
    mod_print("\n[Other]")
    mod_print(f"  /clear                       {BRIGHT_YELLOW} - clear interface{RESET}\n")
    if connected:
        typewriter_effect("Listening for messages ...")
        mod_print(" ")

async def prompt_loop(client: ChatClient):
    session = PromptSession(bottom_toolbar=bottom_toolbar)
    typewriter_effect(CHAT_HEADER, delay=0.05)
    print_menu(client.connected)  # Show options on startup
    with patch_stdout():
            while True:
                try:
                    user_input = await session.prompt_async("> ",style=custom_style)
                    user_input = user_input.strip()
                    #Other
                    if user_input == "/clear":
                            clear_terminal()
                            print_menu(client.connected)
                    else: 
                    #ONLINE
                        if client.connected:
                        #session management
                            if user_input == "/whoami":
                                await client.whoami()
                            elif user_input == "/quit":
                                await client.disconnect()
                                await asyncio.sleep(1)
                                break
                            elif user_input.startswith("/setname ") and len(user_input.split(" "))==2:
                                parts = user_input.split(" ", 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    error_msg("[!] Usage: /setname <new_username>")
                                else:
                                    new_name = parts[1]
                                    await client.set_username(new_name)
                        #channel commands
                            elif user_input.startswith("/create "):
                                parts = user_input.split(" ", 2)
                                if len(parts) < 3:
                                    error_msg("[!] Usage: /create <channel_name> <description>")
                                else:
                                    channel_name = parts[1].strip()
                                    description = parts[2].strip()
                                    await client.create_channel(channel_name, description)
                            elif user_input.startswith("/join "):
                                parts = user_input.split(" ", 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    error_msg("[!] Usage: /join <channel>")
                                else:
                                    await client.join_channel(parts[1].strip())
                            elif user_input.startswith("/channels"):
                                parts = user_input.split(" ",1)
                                offset = 0
                                if len(parts) == 2 and parts[1].isdigit():
                                    offset = int(parts[1])
                                await client.list_channels(offset)
                            elif user_input.startswith("/leave "):
                                parts = user_input.split(" ", 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    error_msg("[!] Usage: /leave <channel>")
                                else:
                                    await client.leave_channel(parts[1].strip())
                            elif user_input.startswith("/info "):
                                parts = user_input.split(" ", 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    error_msg("[!] Usage: /info <channel>")
                                else:
                                    await client.channel_info(parts[1].strip())
                            elif user_input.startswith("/msg"):
                                parts = user_input.split(" ", 2)
                                if len(parts) != 3:
                                    error_msg("[!] Usage: /msg <channel> <message>")
                                else:
                                    channel = parts[1].strip()
                                    message = parts[2].strip()
                                    await client.send_channel_msg(channel, message)
                        #user commands
                            elif user_input.startswith("/users"):
                                parts = user_input.split(" ")
                                if len(parts) == 1:
                                    await client.list_users()
                                elif len(parts) == 2:
                                    if parts[1].isdigit():
                                        await client.list_users(offset=int(parts[1]))
                                    else:
                                        await client.list_users(channel=parts[1])
                                elif len(parts) == 3 and parts[2].isdigit():
                                    await client.list_users(channel=parts[1], offset=int(parts[2]))
                                else:
                                    error_msg("[!] Usage: /users [channel] [offset]")
                            elif user_input.startswith("/whois "):
                                parts = user_input.split(" ", 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    error_msg("[!] Usage: /whois <username>")
                                else:
                                    await client.whois(parts[1].strip())
                            elif user_input.startswith("/dm"):
                                parts = user_input.split(" ", 2)
                                if len(parts) != 3:
                                    error_msg("[!] Usage: /dm <username> <message>")
                                else:
                                    to_user = parts[1].strip()
                                    message = parts[2].strip()
                                    await client.send_dm(to_user, message)
                            else:
                                error_msg("[!] Unknown command.")
                        else:
                    #OFFLINE
                        #session management
                            if user_input == "/connect":
                                await client.connect()
                                if client.connected:
                                    asyncio.create_task(client.receive_loop())
                                    asyncio.create_task(client.ping())
                                    asyncio.create_task(periodic_user_refresh(client))
                                    print_menu(client.connected)
                            elif user_input == "/quit":
                                mod_print(RESET)
                                break
                            else:
                                error_msg("[!] Unknown command.")
                except KeyboardInterrupt:
                    # Handle Ctrl+C
                    break
                except EOFError:
                    # Handle Ctrl+D
                    break

async def periodic_user_refresh(client):
    while client.connected:
        client.silent_update = True
        await client.list_users()
        await asyncio.sleep(60)

def bottom_toolbar():
    content = ""
    time_now = datetime.now().strftime("%H:%M")
    if client.connected:
        content = (f"📡 connected | "
                f"{len(client.joined_channels)} channels | "
                f"💬 {client.dm_count} DMs | "
                f"🧑‍🤝‍🧑 {client.user_count} users | "
                f"🕒 {time_now}")
    else:
        content = (f"📡 disconnected | "
                f"🕒 {time_now}")

    terminal_width = get_terminal_size().columns
    padded = content.ljust(terminal_width)
    return ANSI(
        f"{padded}"
    )

async def main():
    global client 
    client = ChatClient()
    await prompt_loop(client) #cli options

if __name__ == "__main__":
    asyncio.run(main())