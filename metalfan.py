#!/usr/bin/env python3

import glob
import os
import time

from attr import attrs, attrib
import toml

@attrs
class Hwmon():
    path = attrib(convert = lambda p: glob.glob(p)[0])
    probes = attrib(default = [])

@attrs
class Fangroup():
    probe = attrib(default = None)
    temp_min = attrib(default = 20)
    temp_max = attrib(default = 90)
    speed = attrib(default = [])
    speed_min = attrib(default = -1)
    pwm = attrib(default = [])
    pwm_stop = attrib(default = 0)
    pwm_start = attrib(default = 127)
    pwm_min = attrib(default = 63)
    pwm_max = attrib(default = 255)
    pwm_fixed = attrib(default = -1)

def p(path):
    path = path.split("/")
    return str(os.path.join(hwmons[path[0]].path, path[1]))

def echo(value, path):
    with open(p(path), "w") as f:
        f.write(str(value))

def cat(path):
    with open(p(path)) as f:
        return int(f.read().strip())

# Load config
with open("/etc/metalfan.toml") as f:
    config = toml.loads(f.read())
interval = config.get("interval", 1)
hwmons = {name: Hwmon(**params) for name, params in config["hwmon"].items()}
fangroups = [Fangroup(**fg) for fg in config["fangroup"]]

# Set all fans to "manual" mode
for fg in fangroups:
    for pwm in fg.pwm:
        echo(1, f"{pwm}_enable")
        if fg.pwm_fixed >= 0:
            echo(fg.pwm_fixed, pwm)

while True:
    # Gather temps
    for name, hm in hwmons.items():
        hm.temps = dict()
        for pb in hm.probes:
            hm.temps[pb] = cat(f"{name}/{pb}_input") / 1000

    for fg in fangroups:
        if fg.pwm_fixed < 0:
            pb = fg.probe.split("/")
            temp = hwmons[pb[0]].temps[pb[1]]

            if temp < fg.temp_min:
                pwm = fg.pwm_stop
            elif temp > fg.temp_max:
                pwm = fg.pwm_max
            else:
                heat = ((temp - fg.temp_min) / (fg.temp_max - fg.temp_min)) ** 2
                pwm = int((fg.pwm_max - fg.pwm_min) * heat + fg.pwm_min)

            print(pwm)
            for ctl, speed in zip(fg.pwm, fg.speed):
                if pwm > fg.pwm_stop and cat(f"{speed}_input") < fg.speed_min:
                    echo(fg.pwm_start, ctl)
                else:
                    echo(pwm, ctl)

    time.sleep(interval)
