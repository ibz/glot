
import datetime

import utils

def parse(fileobj):
    path = {'points': []}

    for line in fileobj:
        parts = [p.replace("\x00", "") for p in line.split(",")]

        if parts[0] == "INDEX": # first line, skip
            continue

        point = {'time': datetime.datetime.strptime(parts[2] + parts[3], "%y%m%d%H%M%S"),
                 'lat': utils.parse_latlon(parts[4]),
                 'lon': utils.parse_latlon(parts[5]),
                 'ele': int(parts[6])}
        path['points'].append(point)

    return [path]
