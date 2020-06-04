#!/usr/bin/env python3

import json
import time
import sys

from nxtools import *
from nxtools.caspar import *


settings = json.load(open("settings.json"))

c = CasparCG(settings.get("caspar_host"))

def q(cmd):
    start_time = time.time()
    res = c.query(cmd)
    if res:
        logging.goodnews("Command finished in {:.03f}s".format(time.time() - start_time))
    else:
        logging.error("Command failed")

q("CLEAR 1")
q("MIXER 1 RESET")

q("MIXER 1-1 FILL 0   0 .25 .25")
q("MIXER 1-2 FILL .25 0 .25 .25")
q("MIXER 1-3 FILL .5  0 .25 .25")
q("MIXER 1-4 FILL .75 0 .25 .25")
q("MIXER 1-5 FILL 0   .25 .25 .25")
q("MIXER 1-6 FILL .25 .25 .25 .25")
q("MIXER 1-7 FILL .5  .25 .25 .25")
q("MIXER 1-8 FILL .75 .25 .25 .25")
q("MIXER 1-9 FILL 0   .5 .25 .25")
q("MIXER 1-10 FILL .25 .5 .25 .25")
q("MIXER 1-11 FILL .5  .5 .25 .25")
q("MIXER 1-12 FILL .75 .5 .25 .25")
q("MIXER 1-13 FILL 0   .75 .25 .25")
q("MIXER 1-14 FILL .25 .75 .25 .25")
q("MIXER 1-15 FILL .5  .75 .25 .25")
q("MIXER 1-16 FILL .75 .75 .25 .25")

q("PLAY 1-1 CHESS LOOP")
time.sleep(20)
q("PLAY 1-2 FOOD LOOP")
time.sleep(20)
q("PLAY 1-3 COLORS LOOP")
time.sleep(20)
q("PLAY 1-4 DAYLIGHT LOOP")
time.sleep(20)
q("PLAY 1-5 SPACE LOOP")
time.sleep(20)
q("PLAY 1-6 RAYS LOOP")
time.sleep(20)
q("PLAY 1-7 JOURNEY LOOP")
time.sleep(20)
q("PLAY 1-8 SLAM LOOP")
time.sleep(20)
q("PLAY 1-9 wonders LOOP")
time.sleep(20)
