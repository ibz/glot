import sys

import utils

from shapely import wkt

def parse(fileobj, transportation):
    paths = []

    shape = wkt.loads(fileobj.read())

    try:
      list(shape)
    except:
      shape = [shape]

    for polygon in shape:
      path = {'transportation': transportation}
      points = []
      xy = polygon.exterior.xy
      x = [x for x in xy[0]]
      y = [y for y in xy[1]]
      for y, x in zip(y, x):
        points.append(utils.Point(y, x, None, None, None))
      path['points'] = points
      paths.append(path)

    return paths
