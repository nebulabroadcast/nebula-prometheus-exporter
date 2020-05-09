from version import *

settings = {
    "caspar_host" : "localhost",
    "caspar_port" : 5250,
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
