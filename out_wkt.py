import sys

WKT_START = "GEOMETRYCOLLECTION ("
WKT_END = ")"

def gen(paths, output_path=True, output_points=False):
    sys.stdout.write(WKT_START)
    for i, path in enumerate(paths):
        if output_points:
            sys.stdout.write(", ".join("POINT (%s %s)" % (point.lon, point.lat) for point in path['points']))
        if output_path:
            if i != 0 or output_points:
                sys.stdout.write(", ")
            sys.stdout.write("LINESTRING (%s)\n" % ", ".join("%s %s" % (point.lon, point.lat) for point in path['points']))
    sys.stdout.write(WKT_END)
