import datetime

import utils

def parse(fileobj, transportation):
    path = {'transportation': transportation, 'points': []}

    for line in fileobj:
        parts = [p.replace("\x00", "") for p in line.split(",")]

        if parts[0] == "INDEX": # first line, skip
            continue

        lat = utils.parse_latlon(parts[4])
        lon = utils.parse_latlon(parts[5])
        ele = int(parts[6])
        time = datetime.datetime.strptime(parts[2] + parts[3], "%y%m%d%H%M%S")

        if lat is None or lon is None:
            continue

        path['points'].append(utils.Point(lat, lon, ele, time, None))

    return [path]
