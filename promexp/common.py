import sys
import time
import socket
import psutil

from .version import *


HOSTNAME = socket.gethostname()
BOOT_TIME = psutil.boot_time()
RUN_TIME = time.time()
PLATFORM = "windows" if sys.platform == "win32" else "unix"

settings = {
    "caspar_host" : None,
    "amcp_port" : 5250,
    "osc_port" : 6250,
    "prefix" : "nebula",
    "port" : 9731,
    "tags" : {},
    "host" : "",
    "version" : VERSION,
    "smi_path" : None,
    "disk_usage" : True
}


BANNER = """

Nebula Broadcast Prometheus exporter v{version}
https://nebulabroadcast.com

This is an alpha release. Please report issues to
https://github.com/nebulabroadcast/nebula-prometheus-exporter/issues

Listening on {host}:{port}

    - use /metrics for metrics
    - use /shutdown for shutdown (service, not machine)

"""
