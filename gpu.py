import subprocess

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


