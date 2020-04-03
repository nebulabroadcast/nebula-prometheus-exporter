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

VERSION = 0.2
BANNER = """

Nebula Broadcast Prometheus exporter v{version}
https://nebulabroadcast.com

This is an alpha release. Please report issues to
https://github.com/nebulabroadcast/nebula-prometheus-exporter/issues

Listening on {host}:{port}

    - use /metrics for metrics
    - use /shutdown for shutdown (service, not machine)

"""

HOSTNAME = socket.gethostname()
BOOT_TIME = psutil.boot_time()
RUN_TIME = time.time()

settings = {
    "caspar_host" : "localhost",
    "caspar_port" : 5250,
    "prefix" : "nebula",
    "port" : 8080,
    "tags" : {},
    "host" : "",
    "version" : VERSION,
    "smi_path" : None,
}

try:
    with open("settings.json") as f:
        settings.update(json.load(f))
except:
    pass




def get_gpu_stats():
    if not settings["smi_path"]:
        return {}
    rawdata = subprocess.check_output([settings["smi_path"], "-q", "-d", "utilization"]).decode("utf-8")

    modes = [
            "Utilization",
            "GPU Utilization Samples",
            "Memory Utilization Samples",
            "ENC Utilization Samples",
            "DEC Utilization Samples",
        ]
    result = {}
    gpu_id = False
    current_mode = False
    gpu_stats = {}
    for line in rawdata.split("\n"):
        if line.startswith("GPU"):
            if gpu_id:
                result[gpu_id] = gpu_stats

            gpu_stats = []
            gpu_id = line.split(" ")[1].strip()

        for m in modes:
            if line.startswith((" "*4) + m):
                current_mode = m
                break

        if current_mode and line.startswith(" "*8):
            key, value = line.strip().split(":")
            key = key.strip()
            value = float(value.strip().split(" ")[0])
            gpu_stats.append([current_mode.lower(), key.lower(), value])

    if gpu_id:
        result[gpu_id] = gpu_stats

    return result




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
        self.gpu = get_gpu_stats()

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

        for gpuid in self.gpu:
            for mode, key, value in self.gpu[gpuid]:
                if mode != "utilization":
                    continue
                if key == "gpu":
                    key = "usage"
                result += render_metric("gpu_{}".format(key.lower()), value, gpu_id=gpuid)
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

    server = Server()
    while server.httpd.should_run:
        time.sleep(1)
    print("Shutting down HTTP server")