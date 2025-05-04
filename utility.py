import os
from prompt_toolkit.formatted_text.ansi import ANSI
from prompt_toolkit.shortcuts import print_formatted_text
import sys
import time

def typewriter_effect(text: str, delay: float = 0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()  # move to the next line

BOLD = "\033[1m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_WHITE = "\033[97m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_RED="\033[91m"
BRIGHT_CYAN= "\033[96m"
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
UNDERLINE = "\033[4m"
GREY = "\033[90m"
WHITE="\033[37m"   
RESET = "\033[0m"

CHAT_HEADER = f"{BRIGHT_CYAN}Welcome to CLI Chat — Stay connected, securely.{RESET}"

def mod_print(message):
    print_formatted_text(ANSI(message))

def error_msg(message):
    print_formatted_text(ANSI(f"{BRIGHT_RED}{message}{RESET}"))

def server_msg(message):
    print_formatted_text(ANSI(f"{GREY}{message}{RESET}"))

def progress_msg(message):
    print_formatted_text(ANSI(f"{BRIGHT_YELLOW}{message}{RESET}"))

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear') 