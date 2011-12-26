#!/usr/bin/python

from getopt import getopt
import sys

if __name__ == '__main__':
    input_func = None
    input_options = ""

    filter_func = None

    output_func = None
    output_options = {'output_path': True, 'output_points': False}

    optlist, args = getopt(sys.argv[1:], "i:f:o:")
    for opt, val in optlist:
        if opt == "-i":
            if val.startswith("gpx"):
                import in_gpx
                input_func = in_gpx.parse
            elif val.startswith("columbus"):
                import in_columbus
                input_func = in_columbus.parse
            else:
                sys.stderr.write("Invalid input.\n")
                sys.exit(1)
            if ":" in val:
                input_options = val[val.index(":") + 1:]
        elif opt == "-f":
            import filters
            if val.startswith("skip="):
                skip = int(val[len("skip="):])
                filter_func = filters.skip_filter(skip)
            elif val.startswith("name-match-radius="):
                radius = int(val[len("name-match-radius="):])
                filter_func = filters.name_match_filter(radius)
        elif opt == "-o":
            if val.startswith("svg"):
                import out_svg
                output_func = out_svg.gen
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
                if "no-background" in output_objects:
                    output_options['output_background'] = False

    if input_func is None:
        sys.stderr.write("Input not specified. Use -i (gpx|columbus)[:input_options].\n")
        sys.exit(1)

    if output_func is None:
        sys.stderr.write("Output not specified. Use -o (svg|kml)[:output_options]. output_options is an enumeration of path, points, no-background.\n")
        sys.exit(1)

    paths = []
    for filename in args:
        with file(filename) as f:
            paths.extend(input_func(f, input_options))

    if filter_func is not None:
        paths = filter_func(paths)

    output_func(paths, **output_options)
