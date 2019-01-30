#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
from os import getenv
from urllib.parse import urlencode
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from geoalchemy2.elements import WKTElement
from models import RealEstate
import calculations


DATABASE_URL = getenv('DATABASE_URL', 'postgresql://postgres@localhost/wheretolive')
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()


def scrape():
    # Set variables.
    addresses = []
    urls = []
    prices = []
    priceDF = []
    addressDF = []
    combined = None

    try:

        # Loop through first 20 pages each day and add results to dataframe at completion.
        for count in range(1, 2):

            countstr = str(count)

            page_link = f'https://www.realestate.com.au/buy/with-2-bedrooms-between-0-1500000-in-cremorne+point,' \
                f'+nsw+2090%3b+kurraba+point,+nsw+2089%3b+neutral+bay,+nsw+2089%3b+cremorne,+nsw+2090%3b+cammeray,' \
                f'+nsw+2062/list-{countstr}?maxBeds=any'
            page_response = requests.get(page_link, timeout=5)

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

            print(countstr)

        # Clean tags from prices data.

        for price in prices:
            priceDF.append(price)

        # Clean tags from address data.

        for address in addresses:
            addressDF.append(address)

        # Write to dataframe, then to CSV file.

        combined = list(zip(*[addressDF, priceDF, urls]))

        print('All done :)')

    except (ValueError, AttributeError) as e:
        print(e)

    return combined


def save(records):
    for record in records:
        address, price, url = record
        geom = calculations.geocode(address)
        print(geom)
        lng, lat = geom['lng'], geom['lat']
        point = "POINT(%s %s)" % (lng, lat)

        catchment = calculations.get_catchment(lat, lng)
        noisy = calculations.near_noisy_transport(lat, lng)
        #commute = calculations.transport_time(lat, lng)
        commute = calculations.transport_time_google(address)
        realestate = RealEstate(address=address,
                                price=price,
                                url=url,
                                catchment=catchment,
                                commute=commute,
                                noisy=noisy,
                                geom=WKTElement(point, srid=4326))
        session.add(realestate)
    session.commit()


def run():
    scraped_records = scrape()
    save(scraped_records)


if __name__ == '__main__':
    run()
