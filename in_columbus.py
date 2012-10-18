import datetime
import sys

import utils

def parse(fileobj, transportation):
    path = {'transportation': transportation, 'points': []}

    for i, line in enumerate(fileobj, 1):
        parts = [p.replace("\x00", "") for p in line.split(",")]

        if parts[0] == "INDEX": # first line, skip
            continue

        try:
            lat = utils.parse_latlon(parts[4])
            lon = utils.parse_latlon(parts[5])
            ele = int(parts[6])
            time = datetime.datetime.strptime(parts[2] + parts[3], "%y%m%d%H%M%S")
        except:
            sys.stderr.write("Error on line %s\n" % i)
            continue

        if lat is None or lon is None:
            continue

        path['points'].append(utils.Point(lat, lon, ele, time, None))

    return [path]
