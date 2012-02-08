import datetime
import xml.sax
import xml.sax.handler

import utils

class GpxHandler(xml.sax.handler.ContentHandler):
    def __init__(self, transportation):
        self.transportation = transportation

        self.xml_path = []

        self.point = None
        self.path = None

        self.paths = []

        self.TIME_FORMAT = None

    def startElement(self, name, attrs):
        self.xml_path.append(name)

        if name in ['trkpt', 'rtept']:
            self.point = {'lat': utils.parse_latlon(attrs['lat']), 'lon': utils.parse_latlon(attrs['lon'])}
        elif name in ['trk', 'rte']:
            self.path = {'transportation': self.transportation, 'points': []}

    def characters(self, content):
        tail = self.xml_path[-2:]

        if tail == ['trkpt', 'ele'] or tail == ['rtept', 'ele']:
            self.point['ele'] = self.point.get('ele', "") + content
        elif tail == ['trkpt', 'time'] or tail == ['rtept', 'time']:
            self.point['time'] = self.point.get('time', "") + content
        elif tail == ['trkpt', 'name'] or tail == ['rtept', 'name']:
            self.point['name'] = self.point.get('name', "") + content
        elif tail == ['trk', 'name'] or tail == ['rte', 'name']:
            self.path['name'] = self.path.get('name', "") + content

    def endElement(self, name):
        self.xml_path.pop()

        if name in ['trkpt', 'rtept']:
            if 'ele' in self.point:
                self.point['ele'] = float(self.point['ele'].strip())
            if 'time' in self.point:
                if self.TIME_FORMAT is None:
                    for time_format in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"]:
                        try:
                            datetime.datetime.strptime(self.point['time'], time_format)
                            self.TIME_FORMAT = time_format
                        except ValueError:
                            pass
                if self.TIME_FORMAT is None:
                    raise Exception("Can't parse time.")
                self.point['time'] = datetime.datetime.strptime(self.point['time'], self.TIME_FORMAT)
            if 'name' in self.point:
                self.point['name'] = self.point['name'].strip()
            self.path['points'].append(utils.Point(self.point['lat'], self.point['lon'], self.point.get('ele'), self.point.get('time'), self.point.get('name')))
            self.point = None
        elif name in ['trk', 'rte']:
            if 'name' in self.path:
                self.path['name'] = self.path['name'].strip()
            self.paths.append(self.path)
            self.path = None

def parse(fileobj, transportation=None):
    handler = GpxHandler(transportation)
    xml.sax.parse(fileobj, handler)
    return handler.paths
