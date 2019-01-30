import json

import calculations
import scraper


def handler(event, context):

    lat = event.get('queryStringParameters', {}).get('lat')
    lng = event.get('queryStringParameters', {}).get('lng')

    d = dict(transport=None, schools=None, commute=None)
    d['schools'] = calculations.get_catchment(lat, lng)
    d['transport'] = calculations.near_noisy_transport(lat, lng)
    d['commute'] = calculations.transport_time(lat, lng)

    return {"statusCode": 200, "body": json.dumps(d)}


def poll():
    scraper.run()


if __name__ == '__main__':
    poll()
