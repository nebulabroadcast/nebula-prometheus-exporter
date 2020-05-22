#!/usr/bin/env python3

import os
import sys
import time
import json
import subprocess
import psutil
import socket
import traceback

from http.server import HTTPServer, BaseHTTPRequestHandler
import _thread as thread

from defaults import settings, VERSION, BANNER
from gpu import get_gpu_stats
from caspar import CCGTool

from nxtools import *

print ()
print ()

logging.show_time = True

HOSTNAME = socket.gethostname()
BOOT_TIME = psutil.boot_time()
RUN_TIME = time.time()
PLATFORM = "windows" if sys.platform == "win32" else "unix"

try:
    with open("settings.json") as f:
        settings.update(json.load(f))
except:
    pass

#
# Drive usage
#

mountpoint_blacklist = ["/run", "/proc", "/sys", "/dev", "/snap", "/var/lib", "/tmp/snap"]
mountpoint_whitelist = settings["disk_usage"] if type(settings["disk_usage"]) == list else []


def get_disks():
    if not settings["disk_usage"]:
        return
    result = []
    for disk in psutil.disk_partitions(all=True):
        if not all([not disk.mountpoint.startswith(b) for b in mountpoint_blacklist]):
            continue

        if mountpoint_whitelist:
            if not any([disk.mountpoint == b if b == "/" else disk.mountpoint.lower().startswith(b.lower()) for b in mountpoint_whitelist ]):
                continue

        result.append({
                "device" : disk.device,
                "mountpoint" : disk.mountpoint,
                "fstype" : disk.fstype,
            })
    return result


available_disks = get_disks()



def get_disk_usage():
    for disk in available_disks:
        usage = psutil.disk_usage(disk["mountpoint"])
        disk.update({
                "total" : usage.total,
                "free" : usage.free,
                "usage" : usage.percent
            })
        yield disk

#
# Metrics
#

def render_metric(name, value, **tags):
    result = ""
    if settings.get("prefix"):
        result+=str(settings["prefix"])+"_"
    tags["hostname"] = HOSTNAME
    tags.update(settings["tags"])
    result += name + "{"
    result += ", ".join(["{}=\"{}\"".format(k, tags[k]) for k in tags ])
    result += "}"
    result += " " + str(value) + "\n"
    return result





class HWMetrics():
    def __init__(self):
        self.mem = None
        self.swp = None
        self.cpu = None
        self.gpu = None
        self.last_update = 0

    def update(self):
        self.mem = psutil.virtual_memory()
        self.swp = psutil.swap_memory()
        self.cpu = psutil.cpu_percent()
        self.gpu = get_gpu_stats(settings["smi_path"])

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

        for disk in get_disk_usage():
            tags = {
                    "mountpoint" : disk["mountpoint"].replace("\\", "/").rstrip("/"),
                    "fstype" : disk["fstype"],
                }
            result += render_metric("disk_bytes_total", disk["total"] , **tags)
            result += render_metric("disk_bytes_free", disk["free"], **tags)
            result += render_metric("disk_usage", disk["usage"], **tags)


        for i, gpu in enumerate(self.gpu):
            metrics = gpu["utilization"]
            for key in metrics:
                value = metrics[key]
                if key == "gpu":
                    key = "usage"
                result += render_metric("gpu_{}".format(key), value, gpu_id=i)

        if ccgtool:
            for id_channel in ccgtool.profiler:
                for id_layer in ccgtool.profiler[id_channel]:
                    value = ccgtool.profiler[id_channel][id_layer]
                    tags = {
                            "casparcg_host" : ccgtool.address,
                            "casparcg_version" : ccgtool.protocol,
                            "channel" : id_channel,
                            "layer" : id_layer
                        }
                    result += render_metric("caspar_dropped_total", value, **tags)


        return result


metrics = HWMetrics()

if settings["caspar_host"]:
    ccgtool = CCGTool(
            settings["caspar_host"],
            settings["amcp_port"],
            osc_port=settings["osc_port"],
            blocking=False
        )
    ccgtool.start(blocking=False)
else:
    ccgtool = None



class RequestHandler(BaseHTTPRequestHandler):

    def log_request(self, code):
        logging.debug("HTTP request {} finished with status {}".format(self.path, code))

    def make_response(self, data, status=200, mime="text/txt"):
        if type(data) == str:
            data = data.encode("utf-8")
        self.send_response(status)
        self.send_header('Content-type', mime)
        self.send_header('Content-length', len(data))
        self.end_headers()
        self.wfile.write(data)


    def do_GET(self):
        if self.path.startswith("/metrics"):
            try:
                m = metrics()
            except Exception:
                self.make_response("Unable to get metrics\n\n{}".format(traceback.format_exc()), 500)
                return
            self.make_response(m)
            return
        elif self.path.startswith("/shutdown"):
            logging.warning("Shutdown requested")
            self.server.should_run = False
            return

        self.make_response(self.server.parent.get_info)


class Server():
    def __init__(self):
        self.httpd = HTTPServer((settings["host"], settings["port"]), RequestHandler)
        self.httpd.parent = self
        self.httpd.should_run = True
        logging.info("Starting HTTP server: {}:{}".format(settings["host"], settings["port"]))
        thread.start_new_thread(self.httpd.serve_forever, ())

    @property
    def get_info(self):
        return BANNER.format(**settings)


if __name__ == '__main__':
    smi_paths = [
            "c:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
            "/usr/bin/nvidia-smi",
            "/usr/local/bin/nvidia-smi"
        ]

    if settings.get("smi_path"):
        smi_paths.insert(0, settings["smi_path"])

    for f in smi_paths:
        if os.path.exists(f):
            logging.info("nvidia-smi detected. GPU metrics will be available.")
            settings["smi_path"] = f
            break
    else:
        settings["smi_path"] = None

    if "--metrics" in sys.argv:
        metrics = HWMetrics()
        print(metrics())
        sys.exit(0)


    server = Server()
    while server.httpd.should_run:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print()
            break

    logging.info("Shutting down HTTP server")
