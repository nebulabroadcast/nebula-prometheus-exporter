Nebula Prometheus Exporter
==========================

Stand-alone service which provides system metrics for Prometheus in the same
format as Nebula Server. It is intended to run on machines without Nebula
(such as playout servers, encoders).

This is a very early alpha version of the software.


Configuration
-------------

### settings.json

| key | default value | description |
|--|--|--|
`casparcg`    | null        | To enable CasparCG monitoring enter connection `[host, port]` pair, e.g.`["localhost", 5250`]
`prefix`      | `"nebula" ` | Prefix to all presented metrics
`host`        | `""`        | IP address HTTP interface listens on
`port`        | `9731`      | Port HTTP interface listens on
`tags`        | `{}`        | Additional global tags added to each metric
`smi_path`    | `null`      | Path to nvidia-smi binary. If not specified, auto-detect is performed
`disk_usage`  | `true`      | Create disk usage metrics. If set to true, all available disks will be scanned. Can be set to list of mountpoints, e.g. `["c:", "d:"]` or `["/mnt/share"]`

