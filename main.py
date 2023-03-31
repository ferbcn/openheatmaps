import os

from flask import Flask, render_template, request, session, json, abort, make_response
from flask_session import Session

import requests

import bokeh
from bokeh.plotting import figure, show, output_file, ColumnDataSource
# from bokeh.tile_providers import get_provider, Vendors
from bokeh.models import GeoJSONDataSource, ColumnDataSource, HoverTool, LinearColorMapper
from bokeh.embed import file_html
from bokeh.resources import CDN

import json
import math
from pyproj import Proj, transform, Transformer
import numpy as np

allCountries = [
                 "BE", "BG", "CZ", "DK", "DE", "EE", "IE", "EL", "ES", "FR", "HR", "IT", "CY",
                 "LV", "LT", "LU", "HU", "MT", "NL", "AT", "PL", "PT", "RO", "SI", "SK", "FI",
                 "SE", "GR", "GB", "CH", "NO", "IS", "RS", "ME", "MK", "AL", "BA"
                 ]

allFacts = {
                'book': {'tag_key':'shop', 'tag_value':'books'},
                'bank': {'tag_key':'amenity', 'tag_value':'bank'},
                'bar': {'tag_key':'amenity', 'tag_value':'bar'},
                'restaurant': {'tag_key':'amenity', 'tag_value':'restaurant'},
                'station': {'tag_key':'public_transport', 'tag_value':'station'},
                'fuel': {'tag_key':'amenity', 'tag_value':'fuel'},
                'school': {'tag_key':'amenity', 'tag_value':'school'},
                'brothel': {'tag_key':'amenity', 'tag_value':'brothel'},
                'park': {'tag_key': 'leisure', 'tag_value': 'park'},
                'library': {'tag_key': 'amenity', 'tag_value': 'library'},
                'university': {'tag_key': 'amenity', 'tag_value': 'university'},
                'police': {'tag_key': 'amenity', 'tag_value': 'police'},
                'alcohol': {'tag_key': 'shop', 'tag_value': 'alcohol'},
                'hospital': {'tag_key': 'amenity', 'tag_value': 'hospital'},
                }

app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


### Routes ###
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        return render_template("index.html", countries=allCountries, facts=allFacts)

    else:  # request.method == "POST": user tries to login
        #return render_template("error.html", message="Wrong Input Parameters")

        #country = request.POST.get("country", "")
        #fact = country = request.POST.get("fact", "")

        country = request.form.get("country")
        fact = request.form.get("fact")

        print('COUNTRY: ', country)
        print('FACT: ', fact)

        if country == 'all':
            countries = allCountries
            country_in = 'all'
        else:
            countries = []
            country_in = (country[0]+country[1]).upper()
            if country_in not in allCountries:
                return render_template("error.html", message="Wrong Input Parameters")
            countries.append(country_in)

        if fact not in allFacts:
            return render_template("error.html", message="Wrong Input Parameters")
        else:
            tag_key = allFacts[fact]['tag_key']
            tag_value = allFacts[fact]['tag_value']

        print('Using TAGS: ', tag_key, tag_value)

        #arrays for agregated data
        x = []
        y = []
        names = []
        lats = []
        longs = []

        title = ("Heatmap Europe - Countries: {}, Fact: {}").format(country_in, fact)

        p = figure(title=title, background_fill_color="lightgrey", x_axis_type="mercator", y_axis_type="mercator",
                   tools=['wheel_zoom', 'pan', 'box_zoom', 'zoom_in', 'zoom_out', 'reset'])

        #p.add_tile(get_provider(Vendors.CARTODBPOSITRON))
        p.add_tile("CartoDB Positron", retina=True)

        dataFound = False

        # needed to transform cartoraphic data
        projector_x = Proj(init='epsg:4326')
        projector_y = Proj(init='epsg:3857')
        print(projector_x, projector_y)

        for cc in countries:
            os_path = os.path.dirname(__file__)
            json_filename = '{}/static/data/{}_{}/points_{}_{}_{}.json'.format(os_path, tag_key, tag_value, cc, tag_key, tag_value)
            print('processing "'+ json_filename +'"...')

            if not os.path.exists(json_filename):
                print('no file!')
            else:
                dataFound = True

                with open(json_filename) as json_file:
                    json_data = json.load(json_file)
                    geo_data = json.dumps(json_data)
                    geo_source = GeoJSONDataSource(geojson=geo_data)

                data = json_data['features']

                for point in data:
                    try: # not all entries have a name
                        names.append(point['properties']['name'])
                    except KeyError:
                        names.append("none")
                    xdata = point['geometry']['coordinates'][0]
                    ydata = point['geometry']['coordinates'][1]
                    longs.append(xdata)
                    lats.append(ydata)
                    #if ydata > 20 and ydata<70 and xdata > -40 and xdata < 40: #limit data to "europe area"
                        #xd, yd = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), xdata, ydata)
                    trans = Transformer.from_crs("EPSG:4326", "EPSG:3857")
                    xd, yd = trans.transform(ydata, xdata)
                    # print(xd, yd)
                    x.append(xd)
                    y.append(yd)

        if dataFound == False:

            factList = allFacts.keys()
            cStr = 'Possible countries: ' + str(allCountries) + '<br>'
            fStr = 'Possible facts: ' + str(factList) + '<br>'
            return render_template("error.html", message="Wrong Input Parameters")

        binCount = 100
        # heatmap conversion
        H, xedges, yedges = np.histogram2d(x, y, bins=binCount)
        xcenters = (xedges[:-1] + xedges[1:]) / 2
        ycenters = (yedges[:-1] + yedges[1:]) / 2

        max=H.max()
        min=H.min()
        minN=0
        maxN=100

        X = []
        for c in xcenters:
            for i in range(binCount):
                X.append(c)

        Y = []
        for i in range(binCount):
            for c in ycenters:
                Y.append(c)

        Z = []
        for i in range(len(H)):
            array = H[i]
            for q in range(len(array)):
                Z.append((maxN - minN) / (max - min) * (array[q] - max) + maxN)

        print('Plotting {} points in {} bins...'.format(len(x), binCount**2))

        p.circle(X, Y, size=Z, color='firebrick',  alpha=0.7)

        html = file_html([p], CDN, "Heatmaps Europe: {}".format(tag_value))
        #return HttpResponse(html)
        return make_response(html)


if __name__ == "__main__":
    app.run(debug=True)