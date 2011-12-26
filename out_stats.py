import datetime
import math
import sys

from utils import distance

def gen_path_stats(path):
    point_count = len(path['points'])
    has_ele = 'ele' in path['points'][0]
    has_time = 'time' in path['points'][0]

    total_dist = 0

    min_ele = max_ele = None
    ele_sum = 0

    min_time = max_time = None
    moving_time = datetime.timedelta(0)
    stopped_time = datetime.timedelta(0)

    prev_p = None
    for p in path['points']:
        dist = distance(prev_p, p) if prev_p is not None else 0
        total_dist += dist

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
            if dist != 0:
                moving_time += p['time'] - prev_p['time']
            if dist == 0 and prev_p is not None:
                stopped_time += p['time'] - prev_p['time']
        prev_p = p

    avg_ele = ele_sum / point_count

    ele_stdd = math.sqrt(sum((avg_ele - p['ele']) ** 2 for p in path['points']) / point_count) if has_ele else 0

    sys.stdout.write("points: %s, has elevation: %s, has time: %s\n" % (point_count, has_ele, has_time))
    sys.stdout.write("dist: %.2fkm\n" % (total_dist / 1000))
    if has_time:
        time = max_time - min_time
        sys.stdout.write("time: %s\n" % time)
        total_seconds = time.days * 24 * 3600 + time.seconds
        sys.stdout.write("avg speed: %.2fkm/h\n" % (total_dist / total_seconds * 3600 / 1000))
        sys.stdout.write("moving time: %s\n" % moving_time)
        sys.stdout.write("stopped time: %s\n" % stopped_time)
        total_moving_seconds = moving_time.days * 24 * 3600 + moving_time.seconds
        sys.stdout.write("avg speed when moving: %.2fkm/h\n" % (total_dist / total_moving_seconds * 3600 / 1000))
        sys.stdout.write("resolution: %.2f s/point\n" % (float(total_seconds) / float(point_count)))
    if has_ele:
        sys.stdout.write("min ele: %.2fm; max ele: %.2fm; avg ele: %.2fm; ele std dev: %.2fm\n" % (min_ele, max_ele, avg_ele, ele_stdd))

def gen(paths, **__):
    for path in paths:
        gen_path_stats(path)
