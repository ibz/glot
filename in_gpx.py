import datetime
import xml.sax
import xml.sax.handler

import utils

PARSE_TRACKS = 1
PARSE_ROUTES = 2

class GpxHandler(xml.sax.handler.ContentHandler):
    def __init__(self, parse_type):
        if parse_type == PARSE_TRACKS:
            self.PATH_ELEMENT = "trk"
            self.POINT_ELEMENT = "trkpt"
        elif parse_type == PARSE_ROUTES:
            self.PATH_ELEMENT = "rte"
            self.POINT_ELEMENT = "rtept"

        self.xml_path = []

        self.point = None
        self.path = None

        self.paths = []

        self.TIME_FORMAT = None

    def startElement(self, name, attrs):
        self.xml_path.append(name)

        if name == self.POINT_ELEMENT:
            self.point = {'lat': utils.parse_latlon(attrs['lat']), 'lon': utils.parse_latlon(attrs['lon']), 'name': ""}
        elif name == self.PATH_ELEMENT:
            self.path = {'points': []}

    def characters(self, content):
        if self.xml_path[-2:] == [self.PATH_ELEMENT, "name"]:
            self.path['name'] = content.strip()
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "name"]:
            self.point['name'] = content.strip()
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "ele"]:
            self.point['ele'] = self.point.get('ele', "") + content
        elif self.xml_path[-2:] == [self.POINT_ELEMENT, "time"]:
            self.point['time'] = self.point.get('time', "") + content

    def endElement(self, name):
        self.xml_path.pop()

        if name == self.POINT_ELEMENT:
            if 'ele' in self.point:
                self.point['ele'] = float(self.point['ele'].strip())
            if 'time' in self.point:
                if self.TIME_FORMAT is None:
                    for time_format in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"]:
                        try:
                            datetime.datetime.strptime(self.point['time'], time_format)
                            self.TIME_FORMAT = time_format
                        except ValueError:
                            pass
                if self.TIME_FORMAT is None:
                    raise Exception("Can't parse time.")
                self.point['time'] = datetime.datetime.strptime(self.point['time'], self.TIME_FORMAT)
            self.path['points'].append(self.point)
            self.point = None
        elif name == self.PATH_ELEMENT:
            self.paths.append(self.path)
            self.path = None

def parse(fileobj, opts):
    if opts == "" or opts == "trk":
        parse_type = PARSE_TRACKS
    elif opts == "rte":
        parse_type = PARSE_ROUTES
    else:
        raise ValueError("Invalid input options.")

    handler = GpxHandler(parse_type)
    xml.sax.parse(fileobj, handler)
    return handler.paths
