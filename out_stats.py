import datetime
import math
import sys

from utils import distance

def toseconds(t):
    return t.days * 24 * 3600 + t.seconds

def kmph(m, s):
    try:
        return m / s * 3600 / 1000
    except ZeroDivisionError:
        return 0

def gen(paths, **__):
    total_dist = 0
    total_moving_time = datetime.timedelta(0)

    for path in paths:
        point_count = len(path['points'])
        has_ele = 'ele' in path['points'][0]
        has_time = 'time' in path['points'][0]

        dist = 0

        min_ele = max_ele = None
        ele_sum = 0

        min_time = max_time = None
        moving_time = datetime.timedelta(0)
        stopped_time = datetime.timedelta(0)

        prev_p = None
        for p in path['points']:
            d = distance(prev_p, p) if prev_p is not None else 0
            dist += d

            if has_ele:
                if min_ele is None and max_ele is None:
                    min_ele = max_ele = p['ele']
                else:
                    min_ele = min(min_ele, p['ele'])
                    max_ele = max(max_ele, p['ele'])
                ele_sum += p['ele']
            if has_time:
                if min_time is None and max_time is None:
                    min_time = max_time = p['time']
                else:
                    min_time = min(min_time, p['time'])
                    max_time = max(max_time, p['time'])
                if d != 0:
                    moving_time += p['time'] - prev_p['time']
                if d == 0 and prev_p is not None:
                    stopped_time += p['time'] - prev_p['time']
            prev_p = p

        avg_ele = ele_sum / point_count

        ele_stdd = math.sqrt(sum((avg_ele - p['ele']) ** 2 for p in path['points']) / point_count) if has_ele else 0

        sys.stdout.write("points: %s, has elevation: %s, has time: %s\n" % (point_count, has_ele, has_time))
        sys.stdout.write("dist: %.2fkm\n" % (dist / 1000))
        if has_time:
            time = max_time - min_time
            sys.stdout.write("start time: %s\n" % min_time)
            sys.stdout.write("end time: %s\n" % max_time)
            sys.stdout.write("time: %s\n" % time)
            sys.stdout.write("avg speed: %.2fkm/h\n" % kmph(dist, toseconds(time)))
            sys.stdout.write("moving time: %s\n" % moving_time)
            sys.stdout.write("stopped time: %s\n" % stopped_time)
            sys.stdout.write("avg speed when moving: %.2fkm/h\n" % kmph(dist, toseconds(moving_time)))
            sys.stdout.write("resolution: %.2f s/point\n" % (float(toseconds(time)) / float(point_count)))
        if has_ele:
            sys.stdout.write("min ele: %.2fm; max ele: %.2fm; avg ele: %.2fm; ele std dev: %.2fm\n" % (min_ele, max_ele, avg_ele, ele_stdd))
        sys.stdout.write("\n")

        total_dist += dist
        total_moving_time += moving_time

    sys.stdout.write("\n")
    sys.stdout.write("TOTAL dist: %.2fkm\n" % (total_dist / 1000))
    sys.stdout.write("TOTAL moving time: %s\n" % total_moving_time)
    sys.stdout.write("avg speed when moving: %.2fkm/h\n" % kmph(total_dist, toseconds(total_moving_time)))
