__all__ = ["NetworkMetricsProvider"]

import psutil

from .common import settings

interface_blacklist = ["lo"]
interface_whitelist = []

if settings["network_usage"] is True:
    for interface in psutil.net_if_stats().keys():
        istat = psutil.net_if_stats()[interface]
        if not istat.isup:
            continue
        if interface in interface_blacklist:
            continue
        interface_whitelist.append(interface)

elif type(settings["network_usage"]) == list:
    interface_whitelist = settings["network_usage"]



class NetworkMetricsProvider():
    def __init__(self, settings):
        pass

    def __call__(self):
        interfaces = []

        if not settings["network_usage"]:
            return

        netstat = psutil.net_io_counters(pernic=True)
        for interface in netstat.keys():
            if interface in interface_blacklist:
                continue

            if interface not in interface_whitelist:
                continue

            istat = netstat[interface]
            interfaces.append({
                "iface" : interface,
                "sent" : istat.bytes_sent,
                "recv" : istat.bytes_recv
            })
        return interfaces