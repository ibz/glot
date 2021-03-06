from collections import defaultdict

from utils import distance, Point

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

def discard_stopped_filter(paths):
    """Discard all consecutive points with the same coordinates (which means the vechicle was stopped) and that have the same name.
    Should not have any effect on the output, except of slightly reducing the size."""

    for path in paths:
        i = 1
        while i < len(path['points']) - 1:
            p1, p2 = path['points'][i-1:i+1]
            if p1.lat == p2.lat and p1.lon == p2.lon and p1.ele == p2.ele and p1.name == p2.name:
                path['points'].pop(i)
            else:
                i += 1

def skip_filter(skip):
    """Only keep one in every <skip> points.
    Useful to considerably reduce the size of output, but with loss of accuracy.
    """

    def _filter(paths):
        for path in paths:
            keep = lambda i: i == 0 or i % skip == 0 or i == len(path['points']) - 1
            path['points'] = [p for i, p in enumerate(path['points']) if keep(i)]
    return _filter

def name_match_filter(radius):
    """Considers all points within <radius> meters distance from each other and that have the same name to be the same point.
    It will modify the coordinates of all such points to their average.
    """

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
                all_points[point.name].append(point)

        all_points_grouped = dict((name, group_points(points)) for name, points in all_points.iteritems())

        all_group_coords = {}
        for name, groups in all_points_grouped.iteritems():
            all_group_coords[name] = [Point(lat=avg([p.lat for p in group]), lon=avg([p.lon for p in group]), ele=None, time=None, name=None) for group in groups]

        for path in paths:
            for i in range(len(path['points'])):
                point = path['points'][i]
                group_coords = find_closest_point(all_group_coords[point.name], point)
                new_point = Point(group_coords.lat, group_coords.lon, point.ele, point.time, point.name)
                path['points'][i] = new_point

    return _filter
