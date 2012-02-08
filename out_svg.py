from collections import defaultdict
from itertools import izip
import math
import sys

PATH_COLORS = {"plane": "rgb(200,0,0)", "train": "rgb(0,0,0)", "bus": "rgb(0,0,200)", "car": "rgb(0,0,200)", "motorcycle": "rgb(0,0,200)", "boat": "rgb(100,100,100)", "bike": "rgb(0,200,0)", "walk": "rgb(0,200,0)"}

def minmax(l):
    min = max = None
    for e in l:
        if min is None or e < min:
            min = e
        if max is None or e > max:
            max = e
    return min, max

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

def gen_map(paths, output_path=True, output_points=False):
    map_nw = map_se = None

    # need to go through all points once to determine map bounds
    for path in paths:
        for p in path['points']:
            lat, lon = p.lat, p.lon

            if map_nw is None and map_se is None:
                map_nw = {'lat': lat, 'lon': lon}
                map_se = {'lat': lat, 'lon': lon}
            else:
                map_nw['lat'] = max(map_nw['lat'], lat)
                map_nw['lon'] = min(map_nw['lon'], lon)
                map_se['lat'] = min(map_se['lat'], lat)
                map_se['lon'] = max(map_se['lon'], lon)

    if map_nw is None and map_se is None:
        sys.stderr.write("Empty input!\n")
        return

    sys.stdout.write(SVG_START)

    osm_tiles = osm_get_tiles(map_nw, map_se)

    nw_tile = osm_tiles[0]
    map_nw = osm_tile_nw(nw_tile['tile_x'], nw_tile['tile_y'], nw_tile['zoom'])
    se_tile = osm_tiles[-1]
    map_se = osm_tile_nw(se_tile['tile_x'] + 1, se_tile['tile_y'] + 1, se_tile['zoom'])

    for tile in osm_tiles:
        sys.stdout.write(SVG_BACKGROUND % tile)

    min_x, min_y = latlon2xy(map_nw['lat'], map_nw['lon'])
    max_x, max_y = latlon2xy(map_se['lat'], map_se['lon'])

    for path in paths:
        path_color = PATH_COLORS.get(path.get('transportation'), "rgb(0,0,0)")
        point_color = "rgb(255,0,0)"

        prev_x = prev_y = None

        for p in path['points']:
            lat, lon = p.lat, p.lon
            x, y = latlon2xy(lat, lon)

            if output_path and prev_x is not None and prev_y is not None:
                params = {'x1': absolute(prev_x, SVG_WIDTH, min_x, max_x), 'y1': absolute(prev_y, SVG_HEIGHT, min_y, max_y),
                          'x2': absolute(x, SVG_WIDTH, min_x, max_x), 'y2': absolute(y, SVG_HEIGHT, min_y, max_y),
                          'c': path_color}
                sys.stdout.write("<line x1=\"%(x1)s\" y1=\"%(y1)s\" x2=\"%(x2)s\" y2=\"%(y2)s\" style=\"stroke:%(c)s;stroke-width:1;\" />\n" % params)

            if output_points:
                params = {'x': absolute(x, SVG_WIDTH, min_x, max_x), 'y': absolute(y, SVG_HEIGHT, min_y, max_y), 'c': point_color}
                sys.stdout.write("<circle cx=\"%(x)s\" cy=\"%(y)s\" r=\"1\" fill=\"%(c)s\" />\n" % params)

            prev_x, prev_y = x, y

    sys.stdout.write(SVG_END)

def gen_weighted(paths, output_path=True, output_points=False):
    map_nw = map_se = None

    # all segments and points with associated weight
    segments = defaultdict(int)
    points = defaultdict(int)

    # go through all points to compute point/segment weight
    for path in paths:
        svg_path = []
        for p in path['points']:
            lat, lon = p.lat, p.lon

            if map_nw is None and map_se is None:
                map_nw = {'lat': lat, 'lon': lon}
                map_se = {'lat': lat, 'lon': lon}
            else:
                map_nw['lat'] = max(map_nw['lat'], lat)
                map_nw['lon'] = min(map_nw['lon'], lon)
                map_se['lat'] = min(map_se['lat'], lat)
                map_se['lon'] = max(map_se['lon'], lon)

            svg_point = latlon2xy(lat, lon)
            svg_path.append(svg_point)

            if output_points:
                points[svg_point] += 1

        if output_path:
            for (x1, y1), (x2, y2) in izip(svg_path, svg_path[1:]):
                segments[(x1, y1, x2, y2)] += 1

    if map_nw is None and map_se is None:
        sys.stderr.write("Empty input!\n")
        return

    sys.stdout.write(SVG_START)

    min_x, min_y = latlon2xy(map_nw['lat'], map_nw['lon'])
    max_x, max_y = latlon2xy(map_se['lat'], map_se['lon'])

    if output_path:
        min_weight, max_weight = minmax(segments.itervalues())

        for (x1, y1, x2, y2), weight in sorted(segments.iteritems(), key=lambda (s, w): w):
            if min_weight == max_weight:
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
            if min_weight == max_weight:
                color = "rgb(255,0,0)"
            else:
                color = "hsl(0,%s%%,%s%%)" % (10 + absolute(weight, 80, min_weight, max_weight), 80 - absolute(weight, 70, min_weight, max_weight))
            params = {'x': absolute(x, SVG_WIDTH, min_x, max_x), 'y': absolute(y, SVG_HEIGHT, min_y, max_y), 'c': color}
            sys.stdout.write("<circle cx=\"%(x)s\" cy=\"%(y)s\" r=\"1\" fill=\"%(c)s\" />\n" % params)

    sys.stdout.write(SVG_END)
