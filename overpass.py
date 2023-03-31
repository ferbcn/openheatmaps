import overpy
import json
import os
import time
import csv

allFacts = {'book': {'tag_key': 'shop', 'tag_value': 'books'},
            'bank': {'tag_key': 'amenity', 'tag_value': 'bank'},
            'bar': {'tag_key': 'amenity', 'tag_value': 'bar'},
            'restaurant': {'tag_key': 'amenity', 'tag_value': 'restaurant'},
            'station': {'tag_key': 'public_transport', 'tag_value': 'station'},
            'fuel': {'tag_key': 'amenity', 'tag_value': 'fuel'},
            'school': {'tag_key': 'amenity', 'tag_value': 'school'},
            'brothel': {'tag_key': 'amenity', 'tag_value': 'brothel'},
            'park': {'tag_key': 'leisure', 'tag_value': 'park'},
            'library': {'tag_key': 'amenity', 'tag_value': 'library'},
            'university': {'tag_key': 'amenity', 'tag_value': 'university'},
            'police': {'tag_key': 'amenity', 'tag_value': 'police'},
            'alcohol': {'tag_key': 'shop', 'tag_value': 'alcohol'},
            'hospital': {'tag_key': 'amenity', 'tag_value': 'hospital'},
            }


def overpass_load_points(iso_a2='CH', tag_key='amenity', tag_value='cafe'):
    """Load points from OSM with overpy"""

    api = overpy.Overpass()
    r = api.query("""
        ( area["ISO3166-1"="{0}"][admin_level=2]; )->.searchArea;
        ( node[{1}={2}]( area.searchArea );
          way[{1}={2}]( area.searchArea );
          relation[{1}={2}]( area.searchArea );
        );
        out center;""".format(iso_a2, tag_key, tag_value))

    print("Nodes : {}, Ways : {}, Relations : {}".format(
        len(r.nodes), len(r.ways), len(r.relations)))

    coords, names, post_codes, cities = [], [], [], []
    for node in r.nodes:
        coords.append((float(node.lon), float(node.lat)))
        if 'name' in node.tags:
            names.append(node.tags['name'])
        else:
            names.append(None)
        if 'addr:city' in node.tags:
            cities.append(node.tags['addr:city'])
        else:
            cities.append(None)
        if 'addr:postcode' in node.tags:
            post_codes.append(node.tags['addr:postcode'])
        else:
            post_codes.append(None)

    """
    for way in r.ways:
        coords.append((float(way.center_lon), float(way.center_lat)))
        if 'name' in way.tags:
            names.append(way.tags['name'])
        else:
            names.append(None)

    for rel in r.relations:
        coords.append((float(rel.center_lon), float(rel.center_lat)))
        if 'name' in rel.tags:
            names.append(rel.tags['name'])
        else:
            names.append(None)
    """
    return coords, names, cities, post_codes


def save_points_to_file(filepath, coords, names, cities, post_codes, type='json'):
    if type == 'json':
        save_points_geo_json(filepath, coords, names, post_codes, cities)
    elif type == 'csv':
        save_points_csv(filepath, coords, names, post_codes, cities, type="csv")


def save_points_geo_json(filepath, coords, names, post_codes, cities, wgs84=True):
    """Save points to GeoJSON file"""

    features = []
    for coord, name, city, pc in zip(coords, names, cities, post_codes):
        feature = {'type': 'Feature', 'geometry': {}}
        feature['geometry']['type'] = 'Point'
        feature['geometry']['coordinates'] = coord

        if names is not None and name is not None:
            feature['properties'] = {}

            feature['properties']['name'] = name
            feature['properties']['city'] = city
            feature['properties']['post_code'] = pc

        features.append(feature)

    geojson = {}
    geojson['type'] = 'FeatureCollection'
    geojson['features'] = features

    if wgs84:
        # Set CRS as WGS84
        geojson['crs'] = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}

    with open(filepath, 'w') as f:
        json.dump(geojson, f, indent=4)


def save_points_csv(filepath, coords, names, post_codes, cities, wgs84=True, type="csv"):
    """Save points to GeoJSON file"""

    with open(filepath, 'w') as f:
        w = csv.DictWriter(f, ['name', 'long', 'lat', 'post_code', 'city'])
        w.writeheader()

        counter = 0
        for coord, name, pc, city in zip(coords, names, cities, post_codes):
            poi = {}
            if name is not None:
                poi['name'] = name
                poi['long'] = coord[0]
                poi['lat'] = coord[1]
                poi['post_code'] = pc
                poi['city'] = city
                w.writerow(poi)
                counter += 1
        print(f"{counter} records written to file!")


def querry_data_save_to_file(tag_key, tag_value, countries=["CH"], type="json"):
    dirpath = 'data/{}'.format(cat)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    for cc in countries:
        done = False
        filepath = 'data/{}/points_{}_{}_{}.'.format(cat, cc, tag_key, tag_value) + type

        if not os.path.exists(filepath):
            while not done:
                print(cc, tag_key, tag_value)
                try:
                    coords, names, cities, post_codes = overpass_load_points(cc, tag_key, tag_value)
                    print('Number of points : {}'.format(len(coords)))
                    save_points_to_file(filepath, coords, names, post_codes, cities, type=type)
                    done = True
                except overpy.exception.OverpassTooManyRequests:
                    print('Exception: too many requests')
                    time.sleep(10)

        else:
            print('skipping, file: "' + filepath + '" already exists!')


def load_points(filepath):
    """Load points from GeoJSON"""

    coords, names = [], []
    with open(filepath, 'r') as f:
        data = json.load(f)
        if data['type'] == 'MultiPoint':
            coords = data['coordinates']
            names = [None] * len(coords)
        elif data['type'] == 'FeatureCollection':
            for feature in data['features']:
                coords.append(feature['geometry']['coordinates'])
                if 'properties' in feature and 'name' in feature['properties']:
                    names.append(feature['properties']['name'])
                else:
                    names.append(None)
        else:
            raise ValueError('Type \'' + data['type'] + '\' not supported')

    return coords, names


if __name__ == '__main__':
    key = 'amenity'
    cat = 'bar'
    querry_data_save_to_file(key, cat, type="csv")
