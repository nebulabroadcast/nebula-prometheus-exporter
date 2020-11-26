import time
import psutil

from nxtools import *

from .common import *
from .disk import DiskMetricsProvider
from .network import NetworkMetricsProvider
from .gpu import GpuMetricsProvider
from .caspar import CasparMetricsProvider


def render_metric(name, value, **tags):
    result = ""
    if settings.get("prefix"):
        result+=str(settings["prefix"])+"_"
    tags["hostname"] = settings.get("hostname") or HOSTNAME
    tags.update(settings["tags"])
    result += name + "{"
    result += ", ".join(["{}=\"{}\"".format(k, tags[k]) for k in tags ])
    result += "}"
    result += " " + str(value) + "\n"
    return result




class Metrics():
    def __init__(self):
        logging.info("Loading GPU metrics provider")
        self.gpu_provider = GpuMetricsProvider(settings)
        logging.info("Loading disk metrics provider")
        self.disk_provider = DiskMetricsProvider(settings)
        logging.info("Loading CasparCG metrics provider")
        self.caspar_provider = CasparMetricsProvider(settings)
        self.network_metrics = NetworkMetricsProvider(settings)

        self.mem = None
        self.swp = None
        self.cpu = None
        self.gpu = None
        self.diskio = [0,0]
        self.last_update = 0

    def update(self):
        self.mem = psutil.virtual_memory()
        self.swp = psutil.swap_memory()
        self.cpu = psutil.cpu_percent()
        self.gpu = self.gpu_provider()
        self.diskio = psutil.disk_io_counters()

    def __call__(self):
        if time.time() - self.last_update > 2:
            self.update()
            self.last_update = time.time()

        result = ""
        result += render_metric("uptime_seconds", time.time() - BOOT_TIME)
        result += render_metric("cpu_usage", self.cpu)
        result += render_metric("memory_bytes_total", self.mem.total)
        result += render_metric("memory_bytes_free", self.mem.available)
        result += render_metric("memory_usage", 100*((self.mem.total-self.mem.available)/self.mem.total))
        result += render_metric("disk_read_bytes", self.diskio.read_bytes)
        result += render_metric("disk_write_bytes", self.diskio.write_bytes)

        #
        # Disk usage
        #

        for disk in self.disk_provider():
            tags = {
                    "mountpoint" : disk["mountpoint"].replace("\\", "/"),
                    "fstype" : disk["fstype"],
                }
            result += render_metric("disk_bytes_total", disk["total"] , **tags)
            result += render_metric("disk_bytes_free", disk["free"], **tags)
            result += render_metric("disk_usage", disk["usage"], **tags)

        # Network

        for interface in self.network_metrics():
            result += render_metric("network_sent_bytes_total", interface["sent"], interface=interface["iface"] )
            result += render_metric("network_recv_bytes_total", interface["recv"], interface=interface["iface"] )

        #
        # NVIDIA GPU
        #

        for i, gpu in enumerate(self.gpu):
            metrics = gpu["utilization"]
            for key in metrics:
                value = metrics[key]
                if key == "gpu":
                    key = "usage"
                result += render_metric("gpu_{}".format(key), value, gpu_id=i)

        #
        # CasparCG
        #

        if self.caspar_provider.address:
            result += render_metric(
                    "casparcg_idle_seconds",
                    time.time() - self.caspar_provider.last_osc_ts,
                    casparcg_host=self.caspar_provider.address,
                    casparcg_version=self.caspar_provider.protocol,
                )

            for id_channel in self.caspar_provider.fps:
                tags = {
                        "casparcg_host" : self.caspar_provider.address,
                        "casparcg_version" : self.caspar_provider.protocol,
                        "channel" : id_channel,
                    }
                result += render_metric("casparcg_peak_volume", self.caspar_provider.get_peak_volume(id_channel), **tags)
                for id_layer in self.caspar_provider.profiler.get(id_channel, {}):
                    value = self.caspar_provider.profiler[id_channel][id_layer]
                    tags["layer"] = id_layer
                    result += render_metric("casparcg_dropped_total", value, **tags)

        return result
