#!/usr/bin/env python3

import os
import sys
import time
import json
import psutil
import traceback

from http.server import HTTPServer, BaseHTTPRequestHandler
import _thread as thread

from nxtools import *
from promexp import Metrics, settings

logging.show_time = True

try:
    with open("settings.json") as f:
        settings.update(json.load(f))
except:
    pass



class MetricsRequestHandler(BaseHTTPRequestHandler):
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
                m = self.server.parent.metrics()
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


class MetricsServer():
    def __init__(self):
        self.metrics = Metrics()
        self.httpd = HTTPServer((settings["host"], settings["port"]), MetricsRequestHandler)
        self.httpd.parent = self
        self.httpd.should_run = True
        logging.info("Starting HTTP server: {}:{}".format(settings["host"], settings["port"]))
        thread.start_new_thread(self.httpd.serve_forever, ())

    @property
    def get_info(self):
        return "banner is not implemented"




if __name__ == '__main__':
    server = MetricsServer()
    while server.httpd.should_run:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print()
            break

    logging.info("Shutting down HTTP server")
