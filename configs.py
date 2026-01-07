import sys
import platform
import os

USERNAME = "GamerDevIND"
DOWNLOAD_DIR = "minecraft_downloads"
MAX_RAM_GB = 3
MIN_RAM_GB = 3
DESIRED_VERSION = '1.21.10'

OS_TYPE = None
arch_suffix  = ''

if OS_TYPE is None:
    if sys.platform.startswith('win'):
        OS_TYPE = 'windows'
    elif sys.platform.startswith('linux'):
        OS_TYPE = 'linux'
    elif sys.platform.startswith('darwin'):
        OS_TYPE = 'macos'
    else:
        OS_TYPE = 'linux'

    if not arch_suffix.strip():
        arch = platform.machine().lower()

        if OS_TYPE == 'windows':
            if arch in ('x86', 'i386', 'i686'):
                arch_suffix = '-x86'
            elif arch in ('x86_64', 'amd64'):
                arch_suffix = ''
            elif arch in ('arm64', 'aarch64'):
                arch_suffix = '-arm64'
            else:
                arch_suffix = ''
        elif OS_TYPE == 'linux':
            if arch in ('x86_64', 'amd64'):
                arch_suffix = '-x86_64'
            elif arch in ('arm64', 'aarch64'):
                arch_suffix = '-arm64'
            elif arch.startswith('arm'):
                arch_suffix = '-arm32'
            else:
                arch_suffix = ''
        elif OS_TYPE == 'macos':
            if arch in ('x86_64', 'amd64'):
                arch_suffix = ''
            elif arch in ('arm64', 'aarch64'):
                arch_suffix = '-arm64'
            else:
                arch_suffix = ''
        else:
            arch_suffix = ''


classifier = OS_TYPE + arch_suffix
print("Detected native classifier:", classifier)

GAME_DIR = os.path.join(DOWNLOAD_DIR, "game") # you may change "game" to anything of your liking

VERSION_DIR = os.path.join(DOWNLOAD_DIR, "versions", DESIRED_VERSION)

os.makedirs(GAME_DIR, exist_ok=True)
os.makedirs(VERSION_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
