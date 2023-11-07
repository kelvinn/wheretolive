#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import logging
from os import getenv, environ
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from geoalchemy2.elements import WKTElement
from models import RealEstate, Catchments, Association
import calculations
from time import sleep
import sentry_sdk
from sentry_sdk.crons import monitor

SENTRY_DSN = getenv('SENTRY_DSN')


sentry_sdk.init(
    dsn=SENTRY_DSN,

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

logger = logging.getLogger()

DATABASE_URL = getenv('DATABASE_URL', 'postgresql://postgres@localhost/wheretolive')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
REA_COOKIE = getenv('REA_COOKIE', None)

def scrape(num_pages=30):
    # Set variables.
    addresses = []
    urls = []
    prices = []
    priceDF = []
    addressDF = []
    combined = None

    try:
        
        # Loop through first 20 pages each day and add results to dataframe at completion.
        for count in range(1, num_pages):

            countstr = str(count)

            page_link = f'https://www.realestate.com.au/buy/with-2-bedrooms-between-0-1500000-in-cremorne+point,' \
                f'+nsw+2090%3b+kurraba+point,+nsw+2089%3b+neutral+bay,+nsw+2089%3b+cremorne,+nsw+2090%3b+cammeray,' \
                f'+nsw+2062/list-{countstr}?maxBeds=any'

            headers = {
                'User-Agent': USER_AGENT,
                'Authority': 'www.realestate.com.au',
                'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'",
                'Accept-Language': "en-NZ,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,fr;q=0.6'",
                'Cookie': REA_COOKIE
                }
            page_response = requests.get(page_link, headers=headers, timeout=5)

            page_content = BeautifulSoup(page_response.content, "html.parser")

            html = page_content.prettify("utf-8")

            # Set the soup variable to html in bs4.
            soup = BeautifulSoup(html, "html.parser")

            # Parse the prices for each property on the nth page.

            for span in soup.find_all('span', attrs={"class": "property-price"}):
                prices.append(span.contents[0].strip())

            # Parse the urls for each property on nth page.

            for a in soup.find_all('a', attrs={"class": "details-link residential-card__details-link"}, href=True):
                urls.append(a['href'])

            # Parse the address for each property on nth page.

            for a in soup.find_all('a', attrs={"class": "details-link residential-card__details-link"}):
                addresses.append(a.span.contents[0].strip())
            
            sleep(5)

        # Clean tags from prices data.

        for price in prices:
            priceDF.append(price)

        # Clean tags from address data.

        for address in addresses:
            addressDF.append(address)

        # Write to dataframe, then to database

        combined = list(zip(*[addressDF, priceDF, urls]))
 
        print('All done :)')

    except (ValueError, AttributeError) as e:
        print(e)

    return combined


def enrich_records(records):
    enriched = []
    print(f'Starting enrichment...')
    for record in records:
        address, price, url = record
        p = session.query(RealEstate).filter_by(address=address).count()
        if p == 0:
            geom = calculations.geocode(address)

            if geom:
                lng, lat = geom['lng'], geom['lat']
                point = "POINT(%s %s)" % (lng, lat)

                catchments = calculations.get_catchment(lat, lng)
                catchment_gids = [item['gid'] for item in catchments]
                noisy = calculations.near_noisy_transport(lat, lng)
                commute = calculations.transport_time_google(address)

                enriched.append([address, price, url, noisy, commute, catchment_gids, point])

    logger.info(f'Enriched: {len(enriched)} addresses.')
    return enriched


def format_msg(records):
    return 1


def send(msg):

    app_token = environ.get('APP_TOKEN', None)
    user_key = environ.get('USER_KEY', None)

    logger.info(f'Sending the msg: {msg}.')

    r = requests.post('https://api.pushover.net/1/messages.json',
                      data={
                          'token': app_token,
                          'user': user_key,
                          'message': str(msg),
                      })

    return r.status_code


def filter_alerts(records):

    for record in records:
        if record[3] is False and record[4] < 1500 and 1539 in record[5]:
            yield record


def save(enriched):
    for record in enriched:
        address, price, url, noisy, commute, catchment_gids, point = record

        realestate = RealEstate(address=address,
                                price=price,
                                url=url,
                                commute=commute,
                                noisy=noisy,
                                geom=WKTElement(point, srid=4326))

        cs = session.query(Catchments).filter(
            Catchments.gid.in_(catchment_gids)).all()

        # better way to do this?
        for c in cs:
            a = Association()
            a.catchments = c
            realestate.catchments.append(a)
        session.add(realestate)
    try:
        session.commit()
        logger.info(f'Successfully commited records to database.')
        return True
    except Exception as err:
        logging.error(f'Error saving record: {err}')
        return False


@monitor(monitor_slug='daily-crawl')
def crawl():
    scraped_records = scrape()
    enriched = enrich_records(scraped_records)
    save(enriched)
    filtered = list(filter_alerts(enriched))
    if len(filtered) > 0:
        send(filtered)


if __name__ == '__main__':
    if not RealEstate.__table__.exists(engine):
        RealEstate.__table__.create(engine)

    if not Association.__table__.exists(engine):
        Association.__table__.create(engine)
    crawl()
    print("Running scraper...")
