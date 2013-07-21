from collections import defaultdict
import math
import os
import simplejson

import utils

def epsilon_for_zoom(zoom, lat):
    # from http://wiki.openstreetmap.org/wiki/Zoom_levels (metres per pixel)
    return 40075000 * math.cos(math.radians(lat)) / (2 ** (zoom + 8))

def decorate_path_with_xy(path):
    decorated = []
    for p in path:
        x, y = utils.latlng_to_xy(p.lat, p.lon)
        decorated.append({'lat': p.lat, 'lon': p.lon, 'x': x, 'y': y})
    return decorated

def gen_for_zoom(paths, zoom, output_path):
    tiles = defaultdict(lambda: defaultdict(list))
    for i, path in enumerate(paths):
        for point in path['points']:
            tile_x, tile_y = utils.osm_get_tile_xy(point.lat, point.lon, zoom)
            tiles[(zoom, tile_x, tile_y)][i].append(point)
    for tile_key, tile_paths in tiles.iteritems():
        geojson_features = []
        for path_key, path in tile_paths.iteritems():
            path = decorate_path_with_xy(path)
            avg_lat = sum(p['lat'] for p in path) / len(path)
            epsilon = epsilon_for_zoom(zoom, avg_lat)
            path = utils.simplify(path, epsilon)
            geojson_features.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [(p['lon'], p['lat']) for p in path]}})
        with file(os.path.join(output_path, "%s_%s_%s.json" % (tile_key)), 'w') as f:
            simplejson.dump(geojson_features, f)

def gen(paths, min_zoom, max_zoom, output_path):
    for zoom in range(min_zoom, max_zoom + 1):
        gen_for_zoom(paths, zoom, output_path)