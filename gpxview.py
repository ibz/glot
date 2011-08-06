#!/usr/bin/python

from getopt import getopt
import math
import re
import sys
import xml.sax
import xml.sax.handler

LATLON_RE = re.compile(r"^([0-9]+\.[0-9]+)([NSEW])$")
PARSE_TRACKS = 1
PARSE_ROUTES = 2

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
    def __init__(self, parse_type):
        if parse_type == PARSE_TRACKS:
            self.PATH_ELEMENT = "trk"
            self.POINT_ELEMENT = "trkpt"
        elif parse_type == PARSE_ROUTES:
            self.PATH_ELEMENT = "rte"
            self.POINT_ELEMENT = "rtept"

        self.xml_path = []

        self.point = None
        self.path = None

        self.paths = []

    def startElement(self, name, attrs):
        self.xml_path.append(name)

        if name == self.POINT_ELEMENT:
            self.point = {'lat': parse_latlon(attrs['lat']), 'lon': parse_latlon(attrs['lon'])}
        elif name == self.PATH_ELEMENT:
            self.path = {'points': []}

    def characters(self, content):
        if self.xml_path[-2:] == [self.PATH_ELEMENT, "name"]:
            self.path['name'] = content.strip()
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "name"]:
            self.point['name'] = content.strip()

    def endElement(self, name):
        self.xml_path.pop()

        if name == self.POINT_ELEMENT:
            self.path['points'].append(self.point)
            self.point = None
        elif name == self.PATH_ELEMENT:
            self.paths.append(self.path)
            self.path = None

def point_filter(step):
    return lambda points: [p for i, p in enumerate(points) if i == 0 or i == len(points) - 1 or i % step == 0]

def parse_gpx(fileobj, parse_type, filter_func):
    handler = GpxHandler(parse_type)
    xml.sax.parse(fileobj, handler)
    return [{'name': path['name'], 'points': filter_func(path['points'])} for path in handler.paths]

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

def gen_svg(paths):
    segments = []
    min_x, min_y, max_x, max_y = None, None, None, None

    for path in paths:
        for i in range(len(path['points']) - 1):
            p1, p2 = path['points'][i], path['points'][i + 1]

            x1, y1 = latlon2xy(p1['lat'], p1['lon'])
            x2, y2 = latlon2xy(p2['lat'], p2['lon'])

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

KML_START = """<?xml version="1.0" encoding="UTF-8" ?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
<Style id="track_n">
  <LabelStyle><scale>0</scale></LabelStyle>
  <IconStyle><scale>.5</scale><Icon><href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href></Icon></IconStyle>
</Style>
<Style id="track_h">
  <IconStyle><scale>1.2</scale><Icon><href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href></Icon></IconStyle>
</Style>
<StyleMap id="track">
  <Pair><key>normal</key><styleUrl>#track_n</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#track_h</styleUrl></Pair>
</StyleMap>
<Style id="line">
  <LineStyle><color>99ffac59</color><width>6</width></LineStyle>
</Style>
"""

KML_END = "</Document></kml>"

def gen_kml(paths):
    sys.stdout.write(KML_START)
    sys.stdout.write("<Folder><name>Tracks</name>\n")
    for path in paths:
        sys.stdout.write(("<Folder><name>%s</name>\n" % path['name']).encode("utf-8"))
        sys.stdout.write("<Folder><name>Points</name>\n")
        for point in path['points']:
            sys.stdout.write(("<Placemark><name>%(name)s</name><styleUrl>#track</styleUrl><Point><coordinates>%(lon)s,%(lat)s</coordinates></Point></Placemark>\n" % point).encode("utf-8"))
        sys.stdout.write("</Folder>\n")
        sys.stdout.write("<Placemark><name>Path</name><styleUrl>#line</styleUrl><LineString><tessellate>1</tessellate><coordinates>\n")
        for point in path['points']:
            sys.stdout.write("%(lon)s,%(lat)s\n" % point)
        sys.stdout.write("</coordinates></LineString></Placemark>\n")
        sys.stdout.write("</Folder>\n")
    sys.stdout.write("</Folder>\n")
    sys.stdout.write(KML_END)

if __name__ == '__main__':
    filter_func = lambda points: points
    output_func = None
    parse_type = PARSE_TRACKS

    optlist, args = getopt(sys.argv[1:], "s:tro:")
    for opt, val in optlist:
        if opt == "-s":
            filter_func = point_filter(int(val))
        elif opt == "-t":
            parse_type = PARSE_TRACKS
        elif opt == "-r":
            parse_type = PARSE_ROUTES
        elif opt == "-o":
            if val == "svg":
                output_func = gen_svg
            elif val == "kml":
                output_func = gen_kml

    if output_func is None:
        sys.stderr.write("Output not specified. Use -o svg or -o kml.\n")
        sys.exit(1)

    paths = []
    for filename in args:
        with file(filename) as f:
            paths.extend(parse_gpx(f, parse_type, filter_func))
    output_func(paths)
