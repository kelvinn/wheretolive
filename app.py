import json
import requests
from os import getenv
from urllib.parse import urlencode
from flask import Flask, request
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from geoalchemy2.elements import WKTElement
from models import Catchments, Transport

DATABASE_URL = getenv('DATABASE_URL', 'postgresql://postgres@localhost/wheretolive')
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()


app = Flask(__name__)

WORK_COORDS = (-33.866428, 151.206540)


@app.route('/')
def hello_world():
    return 'Hello World!'


def near_noisy_transport(lat, lng):

    point = WKTElement(f"SRID=4326;POINT({lng} {lat})")

    query = session.query(Transport).filter(
        func.ST_DWithin(Transport.geom, point, 0.00015)
    )

    result = False if query.count() == 0 else True

    session.close()

    return result


def transport_time(lat, lng):
    api_key = getenv('TFNSW_API_KEY', None)
    base_url = "https://api.transport.nsw.gov.au/v1/tp/"
    query_type = "trip?"

    work_lat, work_lng = WORK_COORDS

    qdict = dict()
    # add parameters
    qdict["outputFormat"] = "rapidJSON"
    qdict["coordOutputFormat"] = "EPSG:4326"
    qdict["depArrMacro"] = "dep"  # dep after or arr before
    qdict["itdDate"] = "20181217"
    qdict["itdTime"] = "0730"
    qdict["type_origin"] = "coord"
    qdict["name_origin"] = f"{lng}:{lat}:EPSG:4326"  # get location/stop id from stop_finder.py
    qdict["type_destination"] = "coord"
    qdict["name_destination"] = f"{work_lng}:{work_lat}:EPSG:4326"
    qdict["calcNumberOfTrips"] = 5
    qdict["wheelchair"] = ""  # or "on"
    qdict["TfNSWSF"] = "true"
    qdict["version"] = "10.2.1.42"

    # Build query string
    qstring = urlencode(qdict)
    urlsend = base_url + query_type + qstring

    # Build headers
    headers = {'Authorization': 'apikey ' + api_key, 'Accept': 'application/json'}
    response = requests.get(urlsend, headers=headers)

    # Decode and translate to json
    respdict = json.loads(response.content.decode('utf-8'))

    all_trip_durations = []
    for x in range(len(respdict["journeys"])):
        trip_duration = 0
        for y in range(len(respdict["journeys"][x]["legs"])):
            trip_duration += respdict["journeys"][x]["legs"][y]["duration"] / 60
        all_trip_durations.append(trip_duration)
    return min(all_trip_durations)


def get_catchment(lat, lng):
    query = session.query(Catchments).filter(
            Catchments.geom.ST_Intersects(f"POINT({lng} {lat})"))
    schools = [{'catch_type': item.catch_type, 'name': item.use_desc} for item in query.all()]
    session.close()

    return schools


@app.route('/lookup', methods=['GET'])
def lookup():
    lng = request.args.get('lng')
    lat = request.args.get('lat')

    d = dict(transport=False, schools=None, commute=0)
    d['schools'] = get_catchment(lat, lng)
    d['transport'] = near_noisy_transport(lat, lng)
    d['commute'] = transport_time(lat, lng)

    return json.dumps(d)


if __name__ == '__main__':
    app.run()
