#!/usr/bin/python

from getopt import getopt
import os
import re
import sys

import filters

if __name__ == '__main__':
    filter_funcs = [filters.discard_stopped_filter]

    output_func = None
    output_options = {}

    optlist, args = getopt(sys.argv[1:], "f:o:")
    for opt, val in optlist:
        if opt == "-f":
            if val.startswith("skip="):
                skip = int(val[len("skip="):])
                filter_funcs.append(filters.skip_filter(skip))
            elif val.startswith("name-match-radius="):
                radius = int(val[len("name-match-radius="):])
                filter_funcs.append(filters.name_match_filter(radius))
        elif opt == "-o":
            if val.startswith("svg-map"):
                import out_svg
                output_func = out_svg.gen_map
                if ":" in val:
                    output_objects = val[val.index(":") + 1:].split(",")
                    output_options['output_path'] = "path" in output_objects
                    output_options['output_points'] = "points" in output_objects
            elif val.startswith("svg-weighted"):
                import out_svg
                output_func = out_svg.gen_weighted
                if ":" in val:
                    output_objects = val[val.index(":") + 1:].split(",")
                    output_options['output_path'] = "path" in output_objects
                    output_options['output_points'] = "points" in output_objects
            elif val.startswith("plot"):
                import out_plot
                output_func = out_plot.gen
                if ":" in val:
                    params = val[val.index(":") + 1:]
                    if "-" not in params:
                        sys.stderr.write("please pass <xaxis>-<yaxis>[,...]\n.")
                        sys.exit(1)
                    xaxis, yaxis = params.split("-")
                    if xaxis not in ['time', 'distance']:
                        sys.stderr.write("xaxis must be time or distance.\n")
                        sys.exit(1)
                    yaxis = yaxis.split(",")
                    for y in yaxis:
                        if y not in ['speed', 'elevation']:
                            sys.stderr.write("yaxis must be an enumeration of speed and elevation.\n")
                            sys.exit(1)
                    output_options['xaxis'] = xaxis
                    output_options['yaxis'] = yaxis
            elif val.startswith("kml"):
                import out_kml
                output_func = out_kml.gen
                if ":" in val:
                    output_objects = val[val.index(":") + 1:].split(",")
                    output_options['output_path'] = "path" in output_objects
                    output_options['output_points'] = "points" in output_objects
            elif val.startswith("stats"):
                import out_stats
                output_func = out_stats.gen
            else:
                sys.stderr.write("Invalid output.\n")
                sys.exit(1)

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
            sys.stderr.write("Can't guess file type from extension. filename: %s\n" % filename)
            sys.exit(1)

        with file(filename) as f:
            sys.stderr.write("parsing %s...\n" % filename)
            m = re.match(r".*(plane|train|bus|car|motorcycle|boat|bike|walk).*", os.path.basename(filename))
            transportation = m.group(1) if m else None
            paths.extend(input_func(f, transportation=transportation))

    sys.stderr.write("filtering...\n")
    for filter_func in filter_funcs:
        filter_func(paths)

    sys.stderr.write("generating output...\n")
    output_func(paths, **output_options)
