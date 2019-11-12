import getopt
import os
import sys
import xml.etree.ElementTree as ET

"""
Find all the GPX files in the given directory where at least one <tkpt> in inside the given BBOX
"""
def Search(d, s, w, n, e):
	lat_min = max( -90, min(float(s), float(n)))
	lon_min = max(-180, min(float(w), float(e)))
	lat_max = min(  90, max(float(s), float(n)))
	lon_max = min( 180, max(float(w), float(e)))
	
	for path, subdirs, files in os.walk(d):
		for name in files:
			filename = os.path.join(path, name)

			try:
				tree = ET.parse(filename)
			except:
				continue
			
			root = tree.getroot()
			RemoveNamespace(root)
			
			# xpath '//trkpt[@lat >= {0} and @lat <= {1} and @lon >= {2} and @lon <= {3}]'.format(lat_min, lat_max, lon_min, lon_max)
			for trkpt in root.findall('.//trkpt'):
				if lat_min <= float(trkpt.attrib['lat']) <= lat_max:
					if lon_min <= float(trkpt.attrib['lon']) <= lon_max:
						print(filename)
						break

"""
Get rid of namespace that will interfere with the XML parsing
"""
def RemoveNamespace(elem):
	for it in elem.getiterator():
		prefix, has_namespace, postfix = it.tag.partition('}')
		if has_namespace:
			it.tag = postfix

"""
Main
"""
if __name__ == "__main__":
	argv = sys.argv[1:]

	try:
		if len(argv) < 10:
			raise getopt.GetoptError('')
		opts, args = getopt.getopt(argv,"d:s:w:n:e:",["directory","south","west","north","east"])
	except getopt.GetoptError:
		print('--directory <dir> --south <lat> --west <lon> --north <lat> --east <lon>')
		sys.exit(2)
	
	d = r''
	s = -90
	w = -180
	n = 90
	e = 180

	for opt, arg in opts:
		if opt in ("-d", "--directory"):
			d = arg
		elif opt in ("-s", "--south"):
			s = arg
		elif opt in ("-w", "--west"):
			w = arg
		elif opt in ("-n", "--north"):
			n = arg
		elif opt in ("-e", "--east"):
			e = arg

	Search(d, s, w, n, e)