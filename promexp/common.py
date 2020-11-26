import sys
import time
import socket
import psutil

from .version import *
from .branding import BANNER, PREFIX

HOSTNAME = socket.gethostname()
BOOT_TIME = psutil.boot_time()
RUN_TIME = time.time()
PLATFORM = "windows" if sys.platform == "win32" else "unix"

settings = {
    "caspar_host" : None,
    "amcp_port" : 5250,
    "osc_port" : 6250,
    "prefix" : PREFIX,
    "port" : 9731,
    "tags" : {},
    "host" : "",
    "hostname" : None,
    "version" : VERSION,
    "smi_path" : None,
    "disk_usage" : True,
    "network_usage" : True
}
