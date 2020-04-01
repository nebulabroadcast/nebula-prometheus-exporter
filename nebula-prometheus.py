#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import psutil
import socket
import traceback

from http.server import HTTPServer, BaseHTTPRequestHandler
import _thread as thread

VERSION = 0.1
BANNER = """

Nebula Broadcast Prometheus exporter v{}
https://nebulabroadcast.com

This is an alpha release. Please report issues to
https://github.com/nebulabroadcast/nebula-prometheus-exporter/issues

""".format(VERSION)


settings = {
    "caspar_host" : "localhost",
    "caspar_port" : 5250,
    "prefix" : "nebula",
    "host" : "",
    "port" : 8080,
    "smi_path" : "c:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe",
}




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
            gpu_stats.append([current_mode, key, value])

    if gpu_id:
        result[gpu_id] = gpu_stats

    return result







class HWMetrics():
    def __init__(self):
        self.mem = None
        self.swp = None
        self.cpu = None
        self.gpu = None
        self.hostname = socket.gethostname()
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
        result += "{}_uptime{{hostname=\"{}\"}} {}\n".format(settings["prefix"], self.hostname, time.time() - psutil.boot_time())
        result += "{}_cpu{{hostname=\"{}\"}} {}\n".format(settings["prefix"], self.hostname, self.cpu)

        result += "{}_mem{{hostname=\"{}\", mode=\"total\"}} {}\n".format(settings["prefix"], self.hostname, self.mem.total)
        result += "{}_mem{{hostname=\"{}\", mode=\"free\"}} {}\n".format(settings["prefix"], self.hostname, self.mem.available)
        result += "{}_mem{{hostname=\"{}\", mode=\"usage\"}} {}\n".format(
                settings["prefix"],
                self.hostname,
                100*((self.mem.total-self.mem.available)/self.mem.total)
            )

        for gpuid in self.gpu:
            for g in self.gpu[gpuid]:
                result += "{}_gpu{{hostname=\"{}\", gpu_id=\"{}\", mode=\"{}\", key=\"{}\"}} {}\n".format(
                        settings["prefix"],
                        self.hostname,
                        gpuid,
                        g[0], g[1], g[2]
                    )
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
        print (self.get_info)
        thread.start_new_thread(self.httpd.serve_forever, ())

    @property
    def get_info(self):
        return BANNER + """
Listening on {host}:{port}

    - use /metrics for metrics
    - use /shutdown for shutdown (service, not machine)
        """.format(**settings)


if __name__ == '__main__':

    if not os.path.exists(settings["smi_path"]):
        print("Unable to find nvidia-smi. GPU metrics will not be available")
        settings["smi_path"] = None

    server = Server()
    while server.httpd.should_run:
        time.sleep(1)
    print("Shutting down HTTP server")