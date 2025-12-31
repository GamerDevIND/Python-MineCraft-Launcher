import sys

USERNAME  = "GamerDevIND"

DOWNLOAD_DIR = "minecraft_downloads"

MAX_RAM_GB = 3

MIN_RAM_GB = 3

DESIRED_VERSION = '1.21.10'

OS_TYPE = None # set to None to auto-detect

if OS_TYPE is None:
    if sys.platform.startswith('win'):
        OS_TYPE = 'natives-windows'
    elif sys.platform.startswith('linux'):
        OS_TYPE = 'natives-linux'
    elif sys.platform.startswith('darwin'):
        OS_TYPE = 'natives-macos'
    else:
        OS_TYPE = 'natives-linux'