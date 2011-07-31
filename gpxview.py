#!/usr/bin/python

import math
import re
import sys
import xml.sax
import xml.sax.handler

LATLON_RE = re.compile(r"^([0-9]+\.[0-9]+)([NSEW])$")

def parse_latlon(value):
    try:
        return float(value)
    except ValueError:
        match = self.LATLON_RE.match(value)
        if match is not None:
            value, direction = match.groups()
            if direction in ("N", "E"):
                return float(value)
            elif direction in ("S", "W"):
                return -float(value)

class GpxHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.points = list()

    def startElement(self, name, attrs):
        if name == 'trkpt':
            lat = parse_latlon(attrs['lat'])
            lon = parse_latlon(attrs['lon'])
            self.points.append((lat, lon))

def point_filter(step):
    return lambda points: [p for i, p in enumerate(points) if i == 0 or i == len(points) - 1 or i % step == 0]

def parse_gpx(fileobj, filter_func):
    handler = GpxHandler()
    xml.sax.parse(fileobj, handler)
    return filter_func(handler.points)

def latlon2xy(lat, lon):
    return lon, -math.log(math.tan(math.pi / 4 + lat * (math.pi / 180) / 2))

def absolute(v, scale, min_v, max_v):
    return scale * (v - min_v) / (max_v - min_v)

SVG_START = """<?xml version="1.0" standalone="no" ?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="100%" height="100%" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<script xlink:href="SVGPan.js"/>
<g id="viewport">
"""

SVG_END = "</g></svg>"

SVG_HEIGHT = 1000
SVG_WIDTH = 1000

def gen_svg(points):
    segments = []
    min_x, min_y, max_x, max_y = None, None, None, None
    for i in range(len(points) - 1):
        x1, y1 = latlon2xy(*points[i])
        x2, y2 = latlon2xy(*points[i + 1])

        min_x = min(min_x or x1, x1, x2)
        min_y = min(min_y or y1, y1, y2)
        max_x = max(max_x or x1, x1, x2)
        max_y = max(max_y or y1, y1, y2)

        segments.append((x1, y1, x2, y2))

    sys.stdout.write(SVG_START)
    for x1, y1, x2, y2 in segments:
        ax1 = absolute(x1, SVG_WIDTH, min_x, max_x)
        ay1 = absolute(y1, SVG_HEIGHT, min_y, max_y)
        ax2 = absolute(x2, SVG_WIDTH, min_x, max_x)
        ay2 = absolute(y2, SVG_HEIGHT, min_y, max_y)

        sys.stdout.write("""<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke:rgb(100,100,100);stroke-width:1" />\n""" % (ax1, ay1, ax2, ay2))
    sys.stdout.write(SVG_END)

if __name__ == '__main__':
    if sys.argv[1] == "-s":
        step = int(sys.argv[2])
        filter_func = point_filter(step)
        filenames = sys.argv[3:]
    else:
        filter_func = lambda points: points
        filenames = sys.argv[1:]

    points = []
    for filename in filenames:
        with file(filename) as f:
            points.extend(parse_gpx(f, filter_func))
    gen_svg(points)
