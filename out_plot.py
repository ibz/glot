import sys

import matplotlib
matplotlib.use('agg')

import pylab

pylab.grid(True)

from utils import distance

def hours_between(t1, t2):
    delta = t2 - t1
    return delta.days * 24 + float(delta.seconds) / 3600

def gen(paths, xaxis, yaxis):
    xes = []

    eles = []
    speeds = []

    total_dist = 0
    total_time = 0

    prev_p = None

    for path in paths:
        for p in path['points']:
            if prev_p is not None:
                d = float(distance(p, prev_p)) / 1000 # km
                t = hours_between(prev_p.time, p.time) # h

                try:
                    s = d / t # km/h
                except ZeroDivisionError:
                    s = 0

                total_dist += d
                total_time += t
            else:
                s = 0

            if xaxis == 'time':
                xes.append(total_time)
            elif xaxis == 'distance':
                xes.append(total_dist)

            speeds.append(s)
            eles.append(p.ele)

            prev_p = p

    if 'elevation' in yaxis:        
        pylab.plot(xes, eles, label="elevation")
    if 'speed' in yaxis:
        pylab.plot(xes, speeds, label="speed")

    pylab.legend()

    pylab.savefig(sys.stdout, format='png')
