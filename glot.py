#!/usr/bin/python

from getopt import getopt
import os
import re
import sys

if __name__ == '__main__':
    filter_func = None

    output_func = None
    output_options = {}

    optlist, args = getopt(sys.argv[1:], "f:o:")
    for opt, val in optlist:
        if opt == "-f":
            import filters
            if val.startswith("skip="):
                skip = int(val[len("skip="):])
                filter_func = filters.skip_filter(skip)
            elif val.startswith("name-match-radius="):
                radius = int(val[len("name-match-radius="):])
                filter_func = filters.name_match_filter(radius)
        elif opt == "-o":
            if val.startswith("svg-map"):
                import out_svg
                output_func = out_svg.gen_map
            elif val.startswith("svg-weighted"):
                import out_svg
                output_func = out_svg.gen_weighted
            elif val.startswith("plot-elevation"):
                import out_plot
                output_func = out_plot.gen_elevation
            elif val.startswith("kml"):
                import out_kml
                output_func = out_kml.gen
            elif val.startswith("stats"):
                import out_stats
                output_func = out_stats.gen
            else:
                sys.stderr.write("Invalid output.\n")
                sys.exit(1)
            if ":" in val:
                output_objects = val[val.index(":") + 1:].split(",")
                output_options['output_path'] = "path" in output_objects
                output_options['output_points'] = "points" in output_objects

    if output_func is None:
        sys.stderr.write("Output not specified. Use -o (svg-map|svg-weighted|kml)[:output_options]. output_options is an enumeration of path, points.\n")
        sys.exit(1)

    paths = []
    for filename in args:
        if filename.endswith(".gpx"):
            import in_gpx
            input_func = in_gpx.parse
        elif filename.endswith(".CSV"):
            import in_columbus
            input_func = in_columbus.parse
        else:
            sys.stderr.write("Can't guess file type from extension.\n")
            sys.exit(1)

        with file(filename) as f:
            sys.stderr.write("parsing %s...\n" % filename)
            m = re.match(r".*(plane|train|bus|car|ferry|bike|walk).*", os.path.basename(filename))
            transportation = m.group(1) if m else None
            paths.extend(input_func(f, transportation=transportation))

    if filter_func is not None:
        sys.stderr.write("filtering...\n")
        paths = filter_func(paths)

    sys.stderr.write("generating output...\n")
    output_func(paths, **output_options)
