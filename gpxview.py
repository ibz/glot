#!/usr/bin/python

from collections import defaultdict
from getopt import getopt
from itertools import izip
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

def distance(p1, p2):
    d_lat = math.radians(p2['lat'] - p1['lat'])
    d_lon = math.radians(p2['lon'] - p1['lon'])
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(p1['lat'])) * math.cos(math.radians(p2['lat'])) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(6371 * 1000 * c) # distance in meters (radius of the Earth being 6371 * 1000)

def avg(l):
    return sum(l) / len(l)

def minmax(l):
    min = max = None
    for e in l:
        if min is None or e < min:
            min = e
        if max is None or e > max:
            max = e
    return min, max

def find_nearby_point(points, point, radius):
    for p in points:
        if distance(p, point) <= radius:
            return p
    return None

def find_closest_point(points, point):
    closest_point = None
    min_distance = None
    for p in points:
        d = distance(p, point)
        if min_distance is None or d < min_distance:
            min_distance = d
            closest_point = p
    return closest_point

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

def parse_gpx(fileobj, parse_type):
    handler = GpxHandler(parse_type)
    xml.sax.parse(fileobj, handler)
    return handler.paths

def skip_filter(skip):
    def _filter(paths):
        for path in paths:
            keep = lambda i: i == 0 or i % skip == 0 or i == len(path['points']) - 1
            path['points'] = [p for i, p in enumerate(path['points']) if keep(i)]
        return paths
    return _filter

def name_match_filter(radius):
    def find_group(groups, point):
        for group in groups:
            if find_nearby_point(group, point, radius) is not None:
                return group
        return None

    def group_points(points):
        groups = []
        for point in points:
            group = find_group(groups, point)
            if group is None:
                group = []
                groups.append(group)
            group.append(point)
        return groups

    def _filter(paths):
        all_points = defaultdict(list)

        for path in paths:
            for point in path['points']:
                all_points[point['name']].append(point)

        all_points_grouped = dict((name, group_points(points)) for name, points in all_points.iteritems())

        all_group_coords = {}
        for name, groups in all_points_grouped.iteritems():
            all_group_coords[name] = [{'lat': avg([p['lat'] for p in group]), 'lon': avg([p['lon'] for p in group])} for group in groups]

        for path in paths:
            for point in path['points']:
                group_coords = find_closest_point(all_group_coords[point['name']], point)
                point['lat'] = group_coords['lat']
                point['lon'] = group_coords['lon']

        return paths

    return _filter

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

def gen_svg(paths, output_path, output_points):
    min_x = min_y = max_x = max_y = None

    # all segments and points with associated weight
    segments = defaultdict(int)
    points = defaultdict(int)

    for path in paths:
        svg_path = []
        for p in path['points']:
            x, y = latlon2xy(p['lat'], p['lon'])

            svg_path.append((x, y))

            if min_x is None or x < min_x:
                min_x = x
            if max_x is None or x > max_x:
                max_x = x
            if min_y is None or y < min_y:
                min_y = y
            if max_y is None or y > max_y:
                max_y = y

            if output_points:
                points[(x, y)] += 1

        if output_path:
            for (x1, y1), (x2, y2) in izip(svg_path, svg_path[1:]):
                segments[(x1, y1, x2, y2)] += 1

    sys.stdout.write(SVG_START)

    if output_path:
        min_weight, max_weight = minmax(segments.itervalues())

        for (x1, y1, x2, y2), weight in sorted(segments.iteritems(), key=lambda (s, w): w):
            params = {'x1': absolute(x1, SVG_WIDTH, min_x, max_x), 'y1': absolute(y1, SVG_HEIGHT, min_y, max_y),
                      'x2': absolute(x2, SVG_WIDTH, min_x, max_x), 'y2': absolute(y2, SVG_HEIGHT, min_y, max_y),
                      's': 10 + (absolute(weight, 80, min_weight, max_weight) if min_weight != max_weight else 0),
                      'l': 80 - (absolute(weight, 70, min_weight, max_weight) if min_weight != max_weight else 0)}
            sys.stdout.write("""<line x1="%(x1)s" y1="%(y1)s" x2="%(x2)s" y2="%(y2)s" style="stroke:hsl(240,%(s)s%%,%(l)s%%);stroke-width:1;" />\n""" % params)

    if output_points:
        min_weight, max_weight = minmax(points.itervalues())

        for (x, y), weight in sorted(points.iteritems(), key=lambda (p, w): w):
            params = {'x': absolute(x, SVG_WIDTH, min_x, max_x), 'y': absolute(y, SVG_HEIGHT, min_y, max_y),
                      's': 10 + (absolute(weight, 80, min_weight, max_weight) if min_weight != max_weight else 0),
                      'l': 80 - (absolute(weight, 70, min_weight, max_weight) if min_weight != max_weight else 0)}
            sys.stdout.write("""<circle cx="%(x)s" cy="%(y)s" r="1" fill="hsl(0,%(s)s%%,%(l)s%%)" />\n""" % params)

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

def gen_kml(paths, output_path, output_points):
    sys.stdout.write(KML_START)
    sys.stdout.write("<Folder><name>Tracks</name>\n")
    for path in paths:
        sys.stdout.write(("<Folder><name>%s</name>\n" % path['name']).encode("utf-8"))
        if output_points:
            sys.stdout.write("<Folder><name>Points</name>\n")
            for point in path['points']:
                sys.stdout.write(("<Placemark><name>%(name)s</name><styleUrl>#track</styleUrl><Point><coordinates>%(lon)s,%(lat)s</coordinates></Point></Placemark>\n" % point).encode("utf-8"))
            sys.stdout.write("</Folder>\n")
        if output_path:
            sys.stdout.write("<Placemark><name>Path</name><styleUrl>#line</styleUrl><LineString><tessellate>1</tessellate><coordinates>\n")
            for point in path['points']:
                sys.stdout.write("%(lon)s,%(lat)s\n" % point)
            sys.stdout.write("</coordinates></LineString></Placemark>\n")
        sys.stdout.write("</Folder>\n")
    sys.stdout.write("</Folder>\n")
    sys.stdout.write(KML_END)

if __name__ == '__main__':
    filter_func = None
    output_path = True
    output_points = False
    output_func = None
    parse_type = PARSE_TRACKS

    optlist, args = getopt(sys.argv[1:], "trf:o:")
    for opt, val in optlist:
        if opt == "-t":
            parse_type = PARSE_TRACKS
        elif opt == "-r":
            parse_type = PARSE_ROUTES
        elif opt == "-f":
            if val.startswith("skip="):
                skip = int(val[len("skip="):])
                filter_func = skip_filter(skip)
            elif val.startswith("name-match-radius="):
                radius = int(val[len("name-match-radius="):])
                filter_func = name_match_filter(radius)
        elif opt == "-o":
            if val.startswith("svg"):
                output_func = gen_svg
            elif val.startswith("kml"):
                output_func = gen_kml
            else:
                sys.stderr.write("Invalid output.\n")
                sys.exit(1)
            if ":" in val:
                output_objects = val[val.index(":") + 1:].split(",")
                output_path = "path" in output_objects
                output_points = "points" in output_objects

    if output_func is None:
        sys.stderr.write("Output not specified. Use -o (svg|kml)[:(path|points)[,(path|points)]].\n")
        sys.exit(1)

    paths = []
    for filename in args:
        with file(filename) as f:
            paths.extend(parse_gpx(f, parse_type))

    if filter_func is not None:
        paths = filter_func(paths)

    output_func(paths, output_path, output_points)
