import json

from os import environ

from bottle import route, request, response, template, run
import calculations


def handler(event, context):

    lat = event.get('queryStringParameters', {}).get('lat')
    lng = event.get('queryStringParameters', {}).get('lng')

    d = dict(transport=None, schools=None, commute=None)
    d['schools'] = calculations.get_catchment(lat, lng)
    d['transport'] = calculations.near_noisy_transport(lat, lng)
    d['commute'] = calculations.transport_time(lat, lng)

    return {"statusCode": 200, "body": json.dumps(d)}


if __name__ == '__main__':
    if environ.get('APP_LOCATION') == 'heroku':
        run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))
    else:
        run(host='localhost', port=8080, debug=True)
