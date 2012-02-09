import sys

import matplotlib
matplotlib.use('agg')

import pylab

from utils import distance

COLORS = ["blue", "green", "red"]

def hours_between(t1, t2):
    delta = t2 - t1
    return delta.days * 24 + float(delta.seconds) / 3600

def moving_avg(l, window):
    avgs = []
    for i in range(len(l)):
        slice = l[max(i - window, 0) : min(i + window + 1, len(l))]
        avg = float(sum(slice)) / len(slice)
        avgs.append(avg)
    return avgs

def gen(paths, xaxis, yaxis, avg_window):
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

    lines = []
    if 'elevation' in yaxis:
        if avg_window is not None:
            eles = moving_avg(eles, avg_window)
        lines.append((eles, "elevation (m)"))
    if 'speed' in yaxis:
        if avg_window is not None:
            speeds = moving_avg(speeds, avg_window)
        lines.append((speeds, "speed (km/h)"))

    figure = pylab.figure()
    ax = None
    for i, line in enumerate(lines):
        if ax is None:
            ax = figure.add_subplot(111)
            ax.grid(True)
            if xaxis == 'time':
                ax.set_xlabel("time (h)")
            elif xaxis == 'distance':
                ax.set_xlabel("distance (km)")
        else:
            ax = ax.twinx()
        ax.plot(xes, line[0], COLORS[i], linewidth=0.8)
        ax.set_ylabel(line[1], color=COLORS[i])

    figure.savefig(sys.stdout, format='png')
