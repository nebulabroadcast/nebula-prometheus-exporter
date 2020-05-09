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

HOSTNAME = socket.gethostname()
BOOT_TIME = psutil.boot_time()
RUN_TIME = time.time()
PLATFORM = "windows" if sys.platform == "win32" else "unix"

try:
    with open("settings.json") as f:
        settings.update(json.load(f))
except:
    pass

def get_gpu_stats(smi_path, request_modes=["utilization"]):
    if not smi_path:
        return {}
    try:
        rawdata = subprocess.check_output([smi_path, "-q", "-d", "utilization"])
    except Exception:
        return {}

    rawdata = rawdata.decode("utf-8")

    modes = [
            ["Utilization",  "utilization"],
            ["GPU Utilization Samples", "gpu-samples"],
            ["Memory Utilization Samples", "mem-samples"],
            ["ENC Utilization Samples", "enc-samples"],
            ["DEC Utilization Samples", "dec-samples"],
        ]
    result = []
    gpu_id = -1
    current_mode = False
    gpu_stats = {}
    for line in rawdata.split("\n"):
        if line.startswith("GPU"):
            if gpu_id > -1:
                result.append(gpu_stats)

            gpu_stats = {"id" : line.split(" ")[1].strip()}
            gpu_id += 1
        for m, mslug in modes:
            if line.startswith((" "*4) + m):
                current_mode = mslug
                break

        if current_mode in request_modes and line.startswith(" "*8):
            key, value = line.strip().split(":")
            key = key.strip()
            try:
                value = float(value.strip().split(" ")[0])
            except:
                value = 0
            if current_mode not in gpu_stats:
                gpu_stats[current_mode] = {}
            gpu_stats[current_mode][key.lower()] =  value

    if gpu_id > -1:
        result.append(gpu_stats)

    return result




def get_disks():
    result = []
    for disk in psutil.disk_partitions(all=True):
        for m in ["/run", "/proc", "/sys", "/dev", "/snap"]:
            if disk.mountpoint.startswith(m):
                break
        else:
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

        if settings["disk_usage"]:
            for disk in get_disk_usage():
                tags = {
                        "mountpoint" : disk["mountpoint"].replace("\\", "/"),
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
        return result


metrics = HWMetrics()


class RequestHandler(BaseHTTPRequestHandler):
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
            print("Shutdown requested")
            self.server.should_run = False
            return

        self.make_response(self.server.parent.get_info)


class Server():
    def __init__(self):
        self.httpd = HTTPServer((settings["host"], settings["port"]), RequestHandler)
        self.httpd.parent = self
        self.httpd.should_run = True
        thread.start_new_thread(self.httpd.serve_forever, ())
        print (self.get_info)

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

    print("Shutting down HTTP server")
