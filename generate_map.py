import numpy as np
import pandas as pd
import zipfile
from xml.dom import minidom  # to read KML
import folium  # create map
from math import atan2, cos, sin, sqrt, radians


## Scraping results
url = "http://vacationwithoutacar.com/PDF/INTERIM_GVRAT_Tracking_Sheet.html"
dfs = pd.read_html(url)

czechs = dfs[0][dfs[0].E == "CZ"].copy()

extra_info = pd.DataFrame.from_dict({'C': ['Richard Bijecek', 'Karla Fejfarova', 'Pavlina Polaskova', 'Petr Simecek'],
                                     'icon': ['male', 'female', 'female', 'male'],
                                     'color': ['darkgreen', 'orange', 'pink', 'darkpurple']})
czechs = czechs.merge(extra_info, how="left", on="C")


## Calculating position

archive = zipfile.ZipFile('GVRAT Course.kml.kmz', 'r')
kmlfile = archive.open('doc.kml').read()

def calc_distance(origin, destination):
        """great-circle distance between two points on a sphere
           from their longitudes and latitudes"""
        lat1, lon1 = origin
        lat2, lon2 = destination
        radius = 3965  # The radius of Earth in miles

        dlat = radians(lat2-lat1)
        dlon = radians(lon2-lon1)
        a = (sin(dlat/2) * sin(dlat/2) + cos(radians(lat1)) * cos(radians(lat2)) *
             sin(dlon/2) * sin(dlon/2))
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        d = radius * c

        return d

xmldoc = minidom.parse(archive.open('doc.kml'))
kml = xmldoc.getElementsByTagName("kml")[0]
document = kml.getElementsByTagName("Document")[0]
placemarks = document.getElementsByTagName("Placemark")
linestring = document.getElementsByTagName("LineString")

nodes = []
for placemark in placemarks:
  nodename = placemark.getElementsByTagName("name")[0].firstChild.data[:-1]
  coords = placemark.getElementsByTagName("coordinates")[0].firstChild.data
  lst1 = coords.split(",")
  longitude = float(lst1[0])
  latitude = float(lst1[1])
  nodes.append((latitude, longitude))

coords = linestring[0].getElementsByTagName("coordinates")[0].firstChild.data

tmp = [x.split(",") for x in coords.split("\n          ")[1:]]
lat_long = [(float(lat), float(long)) for long, lat, _ in tmp]

lat_long_dist = np.array([calc_distance(lat_long[i], lat_long[i+1]) for i in range(len(lat_long) - 1)])
lat_long_dist_cumsum = np.cumsum(lat_long_dist)

def interpolate_points(point1, point2, dist1, dist2, dist):
  alpha = (dist - dist1) / (dist2 - dist1)
  lat = point1[0] + (point2[0] - point1[0]) * alpha
  long = point1[1] + (point2[1] - point1[1]) * alpha
  return lat, long

def find_position_after_k_miles(k):
  k = float(k)
  bp = np.where(lat_long_dist_cumsum >= k)[0].min()
  return interpolate_points(lat_long[bp], lat_long[bp+1], lat_long_dist_cumsum[bp-1], lat_long_dist_cumsum[bp], k)

czechs['position'] = czechs.H.apply(find_position_after_k_miles)


## Map

lat_center = czechs['position'].apply(lambda x: x[0]).mean()
long_center = czechs['position'].apply(lambda x: x[1]).mean()

m = folium.Map(
    width='100%', 
    height='100%',
    location=[lat_center, long_center],
    zoom_start=12
)

folium.PolyLine(lat_long).add_to(m)

for i in range(czechs.shape[0]):
  folium.Marker(czechs.position.iloc[i], tooltip=czechs.C.iloc[i], 
                icon=folium.Icon(icon=czechs.icon.iloc[i], color=czechs.color.iloc[i], prefix="fa"),
                popup="{},\n{}mi,\n{}".format(czechs.C.iloc[i], czechs.H.iloc[i], czechs.position.iloc[i])).add_to(m)

m.save(outfile="docs/index.html")
print('Done\n')
