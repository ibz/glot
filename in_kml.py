import datetime
import xml.sax
import xml.sax.handler

import utils

class KmlHandler(xml.sax.handler.ContentHandler):
    def __init__(self, transportation):
        self.transportation = transportation

        self.xml_path = []

        self.point = None
        self.path = None

        self.paths = []

    def startElement(self, name, attrs):
        self.xml_path.append(name)

        if name in ['LineString', 'LinearRing']:
            self.path = {'transportation': self.transportation, 'points': []}

    def characters(self, content):
        tail = self.xml_path[-2:]
        content = content.strip()
        if not content:
            return
        if tail == ['LineString', 'coordinates'] or tail == ['LinearRing', 'coordinates']:
            self.path['points'] = [utils.Point(lat, lng, ele, None, None) for lng, lat, ele in [map(float, p.split(",")) for p in content.strip().split(" ")]]

    def endElement(self, name):
        self.xml_path.pop()

        if name in ['LineString', 'LinearRing']:
            self.paths.append(self.path)
            self.path = None

def parse(fileobj, transportation=None):
    handler = KmlHandler(transportation)
    xml.sax.parse(fileobj, handler)
    return handler.paths
