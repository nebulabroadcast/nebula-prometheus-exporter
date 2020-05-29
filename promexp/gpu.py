__all__ = ["GpuMetricsProvider"]

import os
import subprocess

from nxtools import *

class GpuMetricsProvider():
    def __init__(self, settings):
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
                self.smi_path = f
                break
        else:
            self.smi_path = None


    def __call__(self, request_modes=["utilization"]):
        if not self.smi_path:
            return {}
        try:
            rawdata = subprocess.check_output([self.smi_path, "-q", "-d", "utilization"])
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
