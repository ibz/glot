#!/usr/bin/python

from collections import defaultdict
import datetime
from getopt import getopt
from itertools import izip
import math
import re
import sys
import xml.sax
import xml.sax.handler

from utils import distance

LATLON_RE = re.compile(r"^([0-9]+\.[0-9]+)([NSEW])$")
PARSE_TRACKS = 1
PARSE_ROUTES = 2

def parse_latlon(value):
    try:
        return float(value)
    except ValueError:
        match = LATLON_RE.match(value)
        if match is not None:
            value, direction = match.groups()
            if direction in ("N", "E"):
                return float(value)
            elif direction in ("S", "W"):
                return -float(value)

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

        self.TIME_FORMAT = None

    def startElement(self, name, attrs):
        self.xml_path.append(name)

        if name == self.POINT_ELEMENT:
            self.point = {'lat': parse_latlon(attrs['lat']), 'lon': parse_latlon(attrs['lon']), 'name': ""}
        elif name == self.PATH_ELEMENT:
            self.path = {'points': []}

    def characters(self, content):
        if self.xml_path[-2:] == [self.PATH_ELEMENT, "name"]:
            self.path['name'] = content.strip()
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "name"]:
            self.point['name'] = content.strip()
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "ele"]:
            self.point['ele'] = self.point.get('ele', "") + content
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "time"]:
            self.point['time'] = self.point.get('time', "") + content

    def endElement(self, name):
        self.xml_path.pop()

        if name == self.POINT_ELEMENT:
            if 'ele' in self.point:
                self.point['ele'] = float(self.point['ele'].strip())
            if 'time' in self.point:
                if self.TIME_FORMAT is None:
                    for time_format in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"]:
                        try:
                            datetime.datetime.strptime(self.point['time'], time_format)
                            self.TIME_FORMAT = time_format
                        except ValueError:
                            pass
                if self.TIME_FORMAT is None:
                    raise Exception("Can't parse time.")
                self.point['time'] = datetime.datetime.strptime(self.point['time'], self.TIME_FORMAT)
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
<script xlink:href="http://svgpan.googlecode.com/svn/trunk/SVGPan.js" />
<g id="viewport">
<rect x="0" y="0" width="1000" height="1000" style="fill:white" />
"""

SVG_END = "</g></svg>"

OSM_TILE_WIDTH = 256
OSM_TILE_HEIGHT = 256

SVG_BACKGROUND = """
<g opacity="0.5">
<image opacity="1" x="%(x)s" y="%(y)s" width="%(w)s" height="%(h)s" xlink:href="http://a.tile.openstreetmap.org/%(zoom)s/%(tile_x)s/%(tile_y)s.png" />
</g>
"""

SVG_WIDTH = 1024
SVG_HEIGHT = 1024

def osm_get_tile(p, zoom):
    lat = math.radians(p['lat'])
    n = 2.0 ** zoom
    tile_x = int((p['lon'] + 180.0) / 360.0 * n)
    tile_y = int((1.0 - math.log(math.tan(lat) + (1 / math.cos(lat))) / math.pi) / 2.0 * n)
    return (tile_x, tile_y)

def osm_tile_nw(tile_x, tile_y, zoom):
    n = 2.0 ** zoom
    lon = tile_x / n * 360.0 - 180.0
    lat = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
    return {'lat': math.degrees(lat), 'lon': lon}

def osm_get_tiles(map_nw, map_se):
    tiles_x = SVG_WIDTH / OSM_TILE_WIDTH
    tiles_y = SVG_HEIGHT / OSM_TILE_HEIGHT
    zoom = 18
    while zoom > 0:
        tile_x, tile_y = osm_get_tile(map_nw, zoom)
        se = osm_tile_nw(tile_x + tiles_x, tile_y + tiles_y, zoom)
        if se['lat'] <= map_se['lat'] and se['lon'] >= map_se['lon']:
            break
        else:
            zoom -= 1

    return [{'x': i * OSM_TILE_WIDTH, 'y': j * OSM_TILE_HEIGHT, 'w': OSM_TILE_WIDTH, 'h': OSM_TILE_HEIGHT,
             'zoom': zoom, 'tile_x': tile_x + i, 'tile_y': tile_y + j}
            for i in xrange(tiles_x) for j in xrange(tiles_y)]

def gen_svg(paths, output_path, output_points, output_background=True):
    map_nw = {}
    map_se = {}

    # all segments and points with associated weight
    segments = defaultdict(int)
    points = defaultdict(int)

    for path in paths:
        svg_path = []
        for p in path['points']:
            lat, lon = p['lat'], p['lon']

            map_nw['lat'] = max(map_nw.get('lat', lat), lat)
            map_nw['lon'] = min(map_nw.get('lon', lon), lon)

            map_se['lat'] = min(map_se.get('lat', lat), lat)
            map_se['lon'] = max(map_se.get('lon', lon), lon)

            svg_point = latlon2xy(lat, lon)
            svg_path.append(svg_point)

            if output_points:
                points[svg_point] += 1

        if output_path:
            for (x1, y1), (x2, y2) in izip(svg_path, svg_path[1:]):
                segments[(x1, y1, x2, y2)] += 1

    sys.stdout.write(SVG_START)

    if output_background:
        osm_tiles = osm_get_tiles(map_nw, map_se)

        nw_tile = osm_tiles[0]
        map_nw = osm_tile_nw(nw_tile['tile_x'], nw_tile['tile_y'], nw_tile['zoom'])
        se_tile = osm_tiles[-1]
        map_se = osm_tile_nw(se_tile['tile_x'] + 1, se_tile['tile_y'] + 1, se_tile['zoom'])

        for tile in osm_tiles:
            sys.stdout.write(SVG_BACKGROUND % tile)

    min_x, min_y = latlon2xy(map_nw['lat'], map_nw['lon'])
    max_x, max_y = latlon2xy(map_se['lat'], map_se['lon'])

    if output_path:
        min_weight, max_weight = minmax(segments.itervalues())

        for (x1, y1, x2, y2), weight in sorted(segments.iteritems(), key=lambda (s, w): w):
            if output_background or min_weight == max_weight:
                color = "rgb(0,0,0)"
            else:
                color = "hsl(240,%s%%,%s%%)" % (10 + absolute(weight, 80, min_weight, max_weight), 80 - absolute(weight, 70, min_weight, max_weight))
            params = {'x1': absolute(x1, SVG_WIDTH, min_x, max_x), 'y1': absolute(y1, SVG_HEIGHT, min_y, max_y),
                      'x2': absolute(x2, SVG_WIDTH, min_x, max_x), 'y2': absolute(y2, SVG_HEIGHT, min_y, max_y),
                      'c': color}
            sys.stdout.write("<line x1=\"%(x1)s\" y1=\"%(y1)s\" x2=\"%(x2)s\" y2=\"%(y2)s\" style=\"stroke:%(c)s;stroke-width:1;\" />\n" % params)

    if output_points:
        min_weight, max_weight = minmax(points.itervalues())

        for (x, y), weight in sorted(points.iteritems(), key=lambda (p, w): w):
            if output_background or min_weight == max_weight:
                color = "rgb(255,0,0)"
            else:
                color = "hsl(0,%s%%,%s%%)" % (10 + absolute(weight, 80, min_weight, max_weight), 80 - absolute(weight, 70, min_weight, max_weight))
            params = {'x': absolute(x, SVG_WIDTH, min_x, max_x), 'y': absolute(y, SVG_HEIGHT, min_y, max_y), 'c': color}
            sys.stdout.write("<circle cx=\"%(x)s\" cy=\"%(y)s\" r=\"1\" fill=\"%(c)s\" />\n" % params)

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
    for i, path in enumerate(paths, 1):
        sys.stdout.write(("<Folder><name>%s</name>\n" % path.get('name', "Track %s" % i)).encode("utf-8"))
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

def gen_path_stats(path):
    point_count = len(path['points'])
    has_ele = 'ele' in path['points'][0]
    has_time = 'time' in path['points'][0]

    total_dist = 0

    min_ele = max_ele = None
    ele_sum = 0

    min_time = max_time = None
    moving_time = datetime.timedelta(0)
    stopped_time = datetime.timedelta(0)

    prev_p = None
    for p in path['points']:
        dist = distance(prev_p, p) if prev_p is not None else 0
        total_dist += dist

        if has_ele:
            if min_ele is None and max_ele is None:
                min_ele = max_ele = p['ele']
            else:
                min_ele = min(min_ele, p['ele'])
                max_ele = max(max_ele, p['ele'])
            ele_sum += p['ele']
        if has_time:
            if min_time is None and max_time is None:
                min_time = max_time = p['time']
            else:
                min_time = min(min_time, p['time'])
                max_time = max(max_time, p['time'])
            if dist != 0:
                moving_time += p['time'] - prev_p['time']
            if dist == 0 and prev_p is not None:
                stopped_time += p['time'] - prev_p['time']
        prev_p = p

    avg_ele = ele_sum / point_count

    ele_stdd = math.sqrt(sum((avg_ele - p['ele']) ** 2 for p in path['points']) / point_count) if has_ele else 0

    sys.stdout.write("points: %s, has elevation: %s, has time: %s\n" % (point_count, has_ele, has_time))
    sys.stdout.write("dist: %.2fkm\n" % (total_dist / 1000))
    if has_time:
        time = max_time - min_time
        sys.stdout.write("time: %s\n" % time)
        total_seconds = time.days * 24 * 3600 + time.seconds
        sys.stdout.write("avg speed: %.2fkm/h\n" % (total_dist / total_seconds * 3600 / 1000))
        sys.stdout.write("moving time: %s\n" % moving_time)
        sys.stdout.write("stopped time: %s\n" % stopped_time)
        total_moving_seconds = moving_time.days * 24 * 3600 + moving_time.seconds
        sys.stdout.write("avg speed when moving: %.2fkm/h\n" % (total_dist / total_moving_seconds * 3600 / 1000))
        sys.stdout.write("resolution: %.2f s/point\n" % (float(total_seconds) / float(point_count)))
    if has_ele:
        sys.stdout.write("min ele: %.2fm; max ele: %.2fm; avg ele: %.2fm; ele std dev: %.2fm\n" % (min_ele, max_ele, avg_ele, ele_stdd))

def gen_stats(paths, **__):
    for path in paths:
        gen_path_stats(path)

if __name__ == '__main__':
    filter_func = None
    output_func = None
    output_options = {'output_path': True, 'output_points': False}
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
            elif val.startswith("stats"):
                output_func = gen_stats
            else:
                sys.stderr.write("Invalid output.\n")
                sys.exit(1)
            if ":" in val:
                output_objects = val[val.index(":") + 1:].split(",")
                output_options['output_path'] = "path" in output_objects
                output_options['output_points'] = "points" in output_objects
                if "no-background" in output_objects:
                    output_options['output_background'] = False

    if output_func is None:
        sys.stderr.write("Output not specified. Use -o (svg|kml)[:output_options]. output_options is an enumeration of path, points, no-background.\n")
        sys.exit(1)

    paths = []
    for filename in args:
        with file(filename) as f:
            paths.extend(parse_gpx(f, parse_type))

    if filter_func is not None:
        paths = filter_func(paths)

    output_func(paths, **output_options)
