#!/usr/bin/env python3

import time
import _thread
import fractions

from nxtools import *
from nxtools.caspar import CasparCG
from nxtools.caspar.caspar import CasparResponse

from pythonosc import dispatcher
from pythonosc import osc_server


class CasparMetricsProvider(object):
    def __init__(self, settings):
        self.stage = {}
        self.fps = {}
        self.profiler = {}
        self.peak_volume = {}

        self.address = settings["caspar_host"]
        self.port = settings["amcp_port"]
        self.osc_address = "0.0.0.0"
        self.osc_port = settings["osc_port"]

        if not self.address:
            return

        self.connect()
        response = self.query("VERSION")
        protocols = {
                "2.3" : 2.2,
                "2.2" : 2.2,
                "2.1" : 2.1,
                "2.0.7" : 2.07,
                "2.0.6" : 2.06
            }
        for p in protocols:
            if response.data.startswith(p):
                logging.info("CasparCG: using parsed protocol {}".format(protocols[p]))
                self.protocol = protocols[p]
                break
        else:
            self.protocol = 2.2
            logging.info("CasparCG: using default protocol 2.06")

        i = 1
        mode_to_fps = {
                "PAL" : (25, 1),
                "NTSC" : (30000, 1001),
                "1080i5000" : (25, 1),
                "1080p5000" : (50, 1),
                "1080i5994" : (30000, 1001),
                "1080p5994" : (50000, 1001),
            }

        while True:
            response = self.query("INFO {}".format(i))
            if not response:
                break
            x = xml(response.data)
            video_mode = x.find("video-mode").text
            fps = mode_to_fps[video_mode]
            logging.info("CasparCG: parsed channel {} FPS: {}".format(i, fps))
            self.fps[i] = fps
            i += 1

        self.start()
        logging.debug("CasparCG: initialization completed")


    def start(self):
        _thread.start_new_thread(self.heartbeat, ())
        _thread.start_new_thread(self.main, ())


    def connect(self):
        logging.info("CasparCG: connecting to server {}:{}".format(self.address, self.port))
        self.caspar = CasparCG(self.address, self.port)
        if self.caspar.connect():
            logging.goodnews("CasparCG: connected")


    def query(self, *args, **kwargs):
        if not self.caspar:
            return CasparResponse(500, "Not connected")
        return self.caspar.query(*args, **kwargs)

    def heartbeat(self):
        while True:
            try:
                response = self.query("VERSION", verbose=False)
                if not response:
                    self.connect()
                time.sleep(5)
            except Exception:
                log_traceback()


    def main(self):
        self.dispatcher = dispatcher.Dispatcher()
        self.osc = osc_server.BlockingOSCUDPServer(
                    (self.osc_address, self.osc_port),
                    self.dispatcher
                )

        self.dispatcher.map("/channel/*/stage/layer/*/", self.parse_stage)
        self.dispatcher.map("/channel/*/framerate", self.parse_framerate)
        self.dispatcher.map("/channel/*/mixer/audio/*", self.parse_volume)
        self.dispatcher.map("/channel/*/output/consume_time", self.parse_consume_time)

        self.dispatcher.set_default_handler(self.parse_null)
        self.osc.serve_forever()

    def parse_null(self, *args):
        pass

    def parse_framerate(self, *args):
        address = args[0].split("/")
        id_channel = int(address[2])
        data = args[1:]
        if self.fps.get(id_channel) != data:
            logging.info("CasparCG: channel {} FPS changed to".format(id_channel, data))
            self.fps[id_channel] = data

    def parse_volume(self, *args):
        address = args[0].split("/")
        id_channel = int(address[2])
        if len(address) == 7 and address[6] == "pFS":
            self.peak_volume[id_channel] = max(args[1], self.peak_volume.get(id_channel, 0))


    def parse_consume_time(self, *args):
        address = args[0].split("/")
        id_channel = int(address[2])
        data = args[1]

        if data > 1/self.get_fps(id_channel):
            logging.warning("CasparCG: dropped frame on channel {}".format(id_channel))


    def parse_stage(self, *args):
        address = args[0].split("/")
        data =  args[1:]
        id_channel = int(address[2])
        layer = int(address[5])
        key = "/".join(address[6:])
        if not id_channel in self.stage:
            self.stage[id_channel] = {}

        if not layer in self.stage[id_channel]:
            self.stage[id_channel][layer] = {}

        self.stage[id_channel][layer][key] = data

        if key == "profiler/time":
            treal, texp = data
            if treal > texp:
                if not id_channel in self.profiler:
                    self.profiler[id_channel] = {}
                if not layer in self.profiler[id_channel]:
                    self.profiler[id_channel][layer] = 0

                logging.warning("CasparCG: drop frame detected on channel {} layer {}".format(id_channel, layer))
                self.profiler[id_channel][layer] += 1


    def get_peak_volume(self, id_channel):
        result = self.peak_volume.get(id_channel, 0)
        self.peak_volume[id_channel] = 0
        return result

    def get_fps(self, id_channel):
        fps_n, fps_d = self.fps.get(id_channel, (25, 1))
        return fractions.Fraction(fps_d, fps_n)


    def get_layer(self, id_channel=1, id_layer=10):
        try:
            lsrc = self.stage[id_channel][id_layer]
        except KeyError:
            return default_layer_info

        current = lsrc.get("foreground/file/name")
        current = os.path.splitext(current[0])[0] if current else False

        cued = lsrc.get("background/file/name")
        cued = os.path.splitext(cued[0])[0] if cued else False

        paused = lsrc.get("foreground/paused")
        paused = paused[0] if paused else False

        fg_producer = lsrc.get("foreground/producer")
        if fg_producer and fg_producer[0] == "decklink":
            is_live = True
        else:
            is_live = False

        bkg_producer = lsrc.get("background/producer")
        bkg_producer = bkg_producer[0] if bkg_producer else "empty"
        if bkg_producer == "empty":
            if "background/file/name" in lsrc:
                del(lsrc["background/file/name"])
            cued = False

        poss, durs = lsrc.get("foreground/file/time", (0,0))

        if is_live:
            pos = dur = 0
        else:
            fps = self.get_fps(id_channel)
            pos = int(poss * fps)
            dur = int(durs * fps)

        return {
                "current" : current,
                "cued" :  cued,
                "paused" : paused,
                "pos" : pos,
                "dur" : dur,
                "live" : is_live
            }
