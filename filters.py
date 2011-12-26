from collections import defaultdict

from utils import distance

def avg(l):
    return sum(l) / len(l)

def find_nearby_point(points, point, radius):
    for p in points:
        if distance(p, point) <= radius:
            return p
    return None

def find_closest_point(points, point):
    closest_point = None
    min_distance = None
    for p in points:
        d = distance(p, point)
        if min_distance is None or d < min_distance:
            min_distance = d
            closest_point = p
    return closest_point

def skip_filter(skip):
    def _filter(paths):
        for path in paths:
            keep = lambda i: i == 0 or i % skip == 0 or i == len(path['points']) - 1
            path['points'] = [p for i, p in enumerate(path['points']) if keep(i)]
        return paths
    return _filter

def name_match_filter(radius):
    def find_group(groups, point):
        for group in groups:
            if find_nearby_point(group, point, radius) is not None:
                return group
        return None

    def group_points(points):
        groups = []
        for point in points:
            group = find_group(groups, point)
            if group is None:
                group = []
                groups.append(group)
            group.append(point)
        return groups

    def _filter(paths):
        all_points = defaultdict(list)

        for path in paths:
            for point in path['points']:
                all_points[point['name']].append(point)

        all_points_grouped = dict((name, group_points(points)) for name, points in all_points.iteritems())

        all_group_coords = {}
        for name, groups in all_points_grouped.iteritems():
            all_group_coords[name] = [{'lat': avg([p['lat'] for p in group]), 'lon': avg([p['lon'] for p in group])} for group in groups]

        for path in paths:
            for point in path['points']:
                group_coords = find_closest_point(all_group_coords[point['name']], point)
                point['lat'] = group_coords['lat']
                point['lon'] = group_coords['lon']

        return paths

    return _filter
