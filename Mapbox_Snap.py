from shapely.geometry import LineString
import datetime
import json
import sys
import time
import urllib.request as UL
import urllib.error
import xml.etree.ElementTree as ET

GPX_FILE = 'd:/old.gpx'
API_KEY = 'pk.eyJ1IjoiYmFsZGFjY2luaSIsImEiOiJjaWg2aHptZDYwYzd5dWpseGF1bzIybHI5In0.ewK90bfsJ8f4xjqZt_mvBQ'

def Split(trkseg, reason):
    next_trkpt = tmp_trkpts.pop()

    try:
        tmp_trkseg = tmp_trksegs[trkseg]
    except:
        tmp_trkseg = []
    tmp_trkseg.append(tuple(tmp_trkpts))
    tmp_trksegs[trkseg] = tmp_trkseg
    print(" Chunk {0:03d} - <trkpt> {1:03d} - Split: {2}".format(len(tmp_trksegs[trkseg]), len(tmp_trkpts), reason))

    tmp_trkpts.clear()
    tmp_trkpts.append(last_trkpt)
    tmp_trkpts.append(next_trkpt)


def MakeLineString(trkpts):
    coords = []
    for curr_trkpt in trkpts:
        curr_coord = [float(curr_trkpt.attrib['lon']), float(curr_trkpt.attrib['lat'])]
        coords.append(curr_coord)

    try:
        return LineString(coords)
    except ValueError:
        return LineString()


def RemoveNamespace(elem):
    """
    Get rid of namespace that will interfere with the XML parsing
    """
    for it in elem.getiterator():
        prefix, has_namespace, postfix = it.tag.partition('}')
        if has_namespace:
            it.tag = postfix


"""
Phase 1
"""
tmp_trkpts = []
tmp_trksegs = {}

try:
    tree = ET.parse(GPX_FILE)

except:
    print("KO - Parse error GPX_FILE.")
    sys.exit(1)

gpx = tree.getroot()
RemoveNamespace(gpx)

trksegs = gpx.findall(".//trkseg")
print("<gpx> has {0} <trkseg>".format(len(trksegs)))

for trkseg in trksegs:
    print('Processing {0}'.format(trkseg))
    tmp_trkpts.clear()
    for curr_trkpt in trkseg.findall(".//trkpt"):
        curr_coord = [float(curr_trkpt.attrib['lon']), float(curr_trkpt.attrib['lat'])]

        try:
            last_trkpt = tmp_trkpts[-1]
            last_coord = [float(last_trkpt.attrib['lon']), float(last_trkpt.attrib['lat'])]

            if curr_coord == last_coord:
                trkseg.remove(curr_trkpt)
                continue

        except IndexError:
            pass

        tmp_trkpts.append(curr_trkpt)

        if len(tmp_trkpts) > 100:
            Split(trkseg, "Too many pnts")
        else:
            line_string = MakeLineString(tmp_trkpts)
            if line_string.is_empty:
                continue
            elif line_string.is_closed:
                Split(trkseg, "Close line")
            elif not line_string.is_simple:
                Split(trkseg, "Self-intersecting line")

    if MakeLineString(tmp_trkpts).is_empty:
        sys.exit(1)

    try:
        tmp_trkseg = tmp_trksegs[trkseg]
    except:
        tmp_trkseg = []
    tmp_trkseg.append(tuple(tmp_trkpts))
    tmp_trksegs[trkseg] = tmp_trkseg
    print(" Chunk {0:03d} - <trkpt> {1:03d} - New".format(len(tmp_trksegs[trkseg]), len(tmp_trkpts)))

"""
Phase 2
"""
for trkseg in tmp_trksegs:
    print('Processing {0}'.format(trkseg))
    for i, tmp_trkseg in enumerate(tmp_trksegs[trkseg]):
        coordinates = []
        radiuses = []
        timestamps = []
        """
        coordinates, radiuses and timestamps must have the same length
        """
        for trkpt in tmp_trkseg:
            coordinates.append(trkpt.attrib["lon"] + ',' + trkpt.attrib["lat"])
            radiuses.append(str(20))
            time_parts = trkpt.find('./time').text.split(".")  # Remove the milliseconds
            text = time_parts[0]
            if len(time_parts) > 1:
                text += "Z"
            timestamps.append(str(datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').timestamp()))

        """
        join coordinates, radiuses and timestamps into strings whose elements are separeted by ";"
        """
        coordinates = ";".join(coordinates)
        radiuses = ";".join(radiuses)
        timestamps = ";".join(timestamps)

        """
        Call api.mapbox.com
        """
        url = 'https://api.mapbox.com/matching/v5/mapbox/driving/{0}?access_token={1}&tidy=true&geometries=geojson&radiuses={2}&timestamps={3}'.format(coordinates, API_KEY, radiuses, timestamps)
        print(' Chunk {0:03d} - Url {1}'.format(i, url))
        time.sleep(1)
        request = UL.Request(url)
        try:
            response = UL.urlopen(request)
        except urllib.error.HTTPError as httpError:
            print('KO', url, httpError.read().decode())
            sys.exit(1)
        content = response.read()
        result = json.loads(content)
        """
        Parse the resulting .json file
        """
        # with open('d:/data.json', 'w') as outfile:
        #   json.dump(result, outfile, indent=4)

        if "tracepoints" not in result:
            for trkpt in tmp_trkseg:
                if trkpt in trkseg:
                    trkseg.remove(trkpt)
        else:
            for idx, tracepoint in enumerate(result["tracepoints"]):
                trkpt = tmp_trkseg[idx]
                if tracepoint:
                    trkpt.attrib['lat'] = str(tracepoint['location'][1])
                    trkpt.attrib['lon'] = str(tracepoint['location'][0])
                    name = tracepoint['name']
                    if name:
                        extensions = trkpt.find("extensions")
                        if extensions is None:
                            extensions = ET.SubElement(trkpt, 'extensions')
                        extensions_name = extensions.find("name")
                        if extensions_name is None:
                            extensions_name = ET.SubElement(extensions, 'name')
                        extensions_name.text = name

                else:
                    if trkpt in trkseg:
                        trkseg.remove(trkpt)

gpxtree = ET.ElementTree(gpx)
newfilename = 'd:/new.gpx'
gpxtree.write(newfilename)
