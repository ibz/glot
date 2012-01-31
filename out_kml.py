import sys

KML_START = """<?xml version="1.0" encoding="UTF-8" ?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document>
<Style id="track_n">
  <LabelStyle><scale>0</scale></LabelStyle>
  <IconStyle><scale>.5</scale><Icon><href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href></Icon></IconStyle>
</Style>
<Style id="track_h">
  <IconStyle><scale>1.2</scale><Icon><href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href></Icon></IconStyle>
</Style>
<StyleMap id="track">
  <Pair><key>normal</key><styleUrl>#track_n</styleUrl></Pair>
  <Pair><key>highlight</key><styleUrl>#track_h</styleUrl></Pair>
</StyleMap>
<Style id="line">
  <LineStyle><color>99ffac59</color><width>6</width></LineStyle>
</Style>
"""

KML_END = "</Document></kml>"

def gen(paths, output_path=True, output_points=False):
    sys.stdout.write(KML_START)
    sys.stdout.write("<Folder><name>Tracks</name>\n")
    for i, path in enumerate(paths, 1):
        sys.stdout.write(("<Folder><name>%s</name>\n" % path.get('name', "Track %s" % i)).encode("utf-8"))
        if output_points:
            sys.stdout.write("<Folder><name>Points</name>\n")
            for point in path['points']:
                name = point.get('name', "")
                coordinates = "%(lon)s,%(lat)s" % point
                if 'ele' in point:
                    coordinates = "%s,%s" % (coordinates, point['ele'])
                timestamp = "<TimeStamp><when>%s</when></TimeStamp>" % point['time'].strftime("%Y-%m-%dT%H:%M:%SZ") if 'time' in point else ""
                sys.stdout.write(("<Placemark><name>%s</name><styleUrl>#track</styleUrl><Point><coordinates>%s</coordinates></Point>%s</Placemark>\n"
                                  % (name, coordinates, timestamp)).encode("utf-8"))
            sys.stdout.write("</Folder>\n")
        if output_path:
            sys.stdout.write("<Placemark><name>Path</name><styleUrl>#line</styleUrl><LineString><tessellate>1</tessellate><coordinates>\n")
            for point in path['points']:
                sys.stdout.write("%(lon)s,%(lat)s\n" % point)
            sys.stdout.write("</coordinates></LineString></Placemark>\n")
        sys.stdout.write("</Folder>\n")
    sys.stdout.write("</Folder>\n")
    sys.stdout.write(KML_END)
