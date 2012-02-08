import sys

import matplotlib
matplotlib.use('agg')

import pylab

pylab.grid(True)

from utils import distance

def gen(paths, elevation, speed):
    eles = []
    speeds = []
    dists = []
    total_dist = 0
    prev_p = None
    for path in paths:
        for p in path['points']:
            if prev_p is not None:
                d = float(distance(p, prev_p))
                try:
                    s = d / (p.time - prev_p.time).seconds
                except ZeroDivisionError:
                    s = 0

                total_dist += d / 1000
            else:
                s = 0

            speeds.append(s)
            dists.append(total_dist)
            eles.append(p.ele)

            prev_p = p

    if elevation:
        pylab.plot(dists, eles, label="elevation")
    if speed:
        pylab.plot(dists, speeds, label="speed")

    pylab.legend()

    pylab.savefig(sys.stdout, format='png')
