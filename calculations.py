import requests
import json
import googlemaps
from datetime import datetime, date
from os import getenv
from urllib.parse import urlencode
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from geoalchemy2.elements import WKTElement
from models import Catchments, Transport

DATABASE_URL = getenv('DATABASE_URL', 'postgresql://postgres@localhost/wheretolive')
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


WORK_COORDS = (-33.866428, 151.206540)
GMAPS_API_KEY = getenv('GMAPS_API_KEY', '123456')


def near_noisy_transport(lat, lng):

    point = WKTElement(f"SRID=4326;POINT({lng} {lat})")

    query = session.query(Transport).filter(
        func.ST_DWithin(Transport.geom, point, 0.0004)
    )

    result = False if query.count() == 0 else True
    session.close()
    return result


def transport_time(lat, lng):
    api_key = getenv('TFNSW_API_KEY', 'dev_tfnsw_api_key_string')
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
    schools = [{'gid': item.gid, 'catch_type': item.catch_type, 'name': item.use_desc} for item in query.all()]

    session.close()
    return schools


def geocode(address):
    gmaps = googlemaps.Client(key=GMAPS_API_KEY)
    geocode_result = gmaps.geocode(address)
    location = [address['geometry']['location'] for address in geocode_result if address][0]
    return location


def transport_time_google(address):
    gmaps = googlemaps.Client(key=GMAPS_API_KEY)
    today = date.today()
    when_depart = datetime(year=today.year, month=today.month, day=today.day, hour=8)
    commute = gmaps.directions(address,
                               "Wynyard Station, Sydney NSW",
                               mode="transit",
                               departure_time=when_depart)
    try:
        total_commute = commute[0]['legs'][0]['duration']['value']
    except IndexError:
        total_commute = 999999

    return total_commute

