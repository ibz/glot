import sys

from utils import distance

def absolute(v, scale, min_v, max_v):
    return scale * (v - min_v) / (max_v - min_v)

SVG_WIDTH = 800
SVG_HEIGHT = 500

SVG_START = """<?xml version="1.0" standalone="no" ?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="100%" height="100%" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="viewport">
<rect x="0" y="0" width="1000" height="1000" style="fill:white" />
"""

SVG_END = "</g></svg>"

def gen_elevation(paths):

    # 1st pass, to compute total distance and min/max elevation
    total_d = 0
    prev_p = None
    min_ele = max_ele = None
    for path in paths:
        for p in path['points']:
            if prev_p is not None:
                total_d += distance(p, prev_p)
            min_ele = min(min_ele or p['ele'], p['ele'])
            max_ele = max(max_ele or p['ele'], p['ele'])

            prev_p = p

    sys.stdout.write(SVG_START)

    prev_d = d = 0
    prev_p = None
    for path in paths:
        for p in path['points']:
            if prev_p is not None:
                d += distance(p, prev_p)
                sys.stdout.write("<line x1=\"%s\" y1=\"%s\" x2=\"%s\" y2=\"%s\" style=\"stroke:rgb(0,0,0);stroke-width:1;\" />\n"
                                 % (absolute(prev_d, SVG_WIDTH, 0, total_d),
                                    SVG_HEIGHT - absolute(prev_p['ele'] if prev_p else 0, SVG_HEIGHT, min_ele, max_ele),
                                    absolute(d, SVG_WIDTH, 0, total_d),
                                    SVG_HEIGHT - absolute(p['ele'], SVG_HEIGHT, min_ele, max_ele)))
            prev_p = p
            prev_d = d

    sys.stdout.write(SVG_END)
