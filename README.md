Nebula Prometheus Exporter
==========================

Stand-alone service which provides system metrics for Prometheus in the same
format as Nebula Server. It is intended to run on machines without Nebula
(such as playout servers, encoders).

Installation
------------

## Windows

Download the latest binary package from releases page, edit `settings.json` file and run the executable.

## Linux

Nebula Prometheus Exporter depends on *psutil* Python module. Install it using `pip3 install psutil` command.

 - Clone this repository
 - Edit `settings.json` file
 - Use `make install` to install nebula-prometheus-exporter systemd unit
 - Run `systemctl enable nebula-prometheus-exporter`
 - Run `systemctl start nebula-prometheus-exporter`

Configuration
-------------

### settings.json

| key | default | description |
|--|--|--|
`caspar_host` | null        | To enable CasparCG monitoring enter server hostname or IP
`amcp_port`   | 5250        | CasparCG AMCP port
`osc_port `   | 6250        | CasparCG OSC port
`prefix`      | `"nebula" ` | Prefix to all presented metrics
`host`        | `""`        | IP address HTTP interface listens on
`port`        | `9731`      | Port HTTP interface listens on
`tags`        | `{}`        | Additional global tags added to each metric
`smi_path`    | `null`      | Path to nvidia-smi binary. If not specified, auto-detect is performed
`disk_usage`  | `true`      | Create disk usage metrics. If set to true, all available disks will be scanned. Can be set to list of mountpoints, e.g. `["c:", "d:"]` or `["/mnt/share"]`

