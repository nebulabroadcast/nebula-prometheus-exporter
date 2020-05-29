__all__ = ["DiskMetricsProvider"]

import psutil

from .common import settings

mountpoint_blacklist = ["/run", "/proc", "/sys", "/dev", "/snap", "/var/lib", "/tmp/snap"]
mountpoint_whitelist = settings["disk_usage"] if type(settings["disk_usage"]) == list else []


class DiskMetricsProvider():
    def __init__(self, settings):
        self.disks = []
        if not settings["disk_usage"]:
            return
        for disk in psutil.disk_partitions(all=True):
            if not all([not disk.mountpoint.startswith(b) for b in mountpoint_blacklist]):
                continue

            if mountpoint_whitelist:
                if not any([disk.mountpoint == b if b == "/" else disk.mountpoint.lower().startswith(b.lower()) for b in mountpoint_whitelist ]):
                    continue

            self.disks.append({
                    "device" : disk.device,
                    "mountpoint" : disk.mountpoint,
                    "fstype" : disk.fstype,
                })

    def __call__(self):
        for disk in self.disks:
            usage = psutil.disk_usage(disk["mountpoint"])
            disk.update({
                    "total" : usage.total,
                    "free" : usage.free,
                    "usage" : usage.percent
                })
            yield disk
