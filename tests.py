import unittest
import responses
from os import getenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import RealEstate, Association
import calculations
import scraper


DATABASE_URL = getenv('DATABASE_URL', 'postgresql://postgres@localhost/wheretolive')
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

RECORDS = [('4/18 Spruson Street, Neutral Bay', 'Auction', '/property-apartment-nsw-neutral+bay-130266522'),
           ('1/15 Morden Street, Cammeray', '$785,000', '/property-apartment-nsw-cammeray-130374818'),
           ('1/295 Ernest Street, Neutral Bay', '$100', '/property-apartment-nsw-neutral+bay-130172302'),
           ('8/23 Harrison Street, Cremorne', 'Contact Agent', '/property-apartment-nsw-cremorne-130216894'),
           ('104/433 Alfred Street, Neutral Bay', '$1,300', '/property-apartment-nsw-neutral+bay-130290086'),
           ('10/140 Holt Avenue, Cremorne', 'Contact Agent', '/property-apartment-nsw-cremorne-130288814')]


class AppTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @responses.activate
    def test_transport_time(self):
        with open(r'data/tfnsw.json') as f:
            sample = f.read()

        responses.add(responses.GET, 'https://api.transport.nsw.gov.au/v1/tp/trip',
                      body=sample, status=200,
                      content_type='application/json')
        result = calculations.transport_time('-33.846206', '151.229796')
        self.assertEqual(38.2, result)

    @responses.activate
    def test_scrape(self):
        with open(r'data/rea.html') as f:
            sample = f.read()

        responses.add(responses.GET, 'https://www.realestate.com.au/buy/with-2-bedrooms-between-0-1500000-in-cremorne+point,+nsw+2090%3b+kurraba+point,+nsw+2089%3b+neutral+bay,+nsw+2089%3b+cremorne,+nsw+2090%3b+cammeray,+nsw+2062/list-1?maxBeds=any',
                      body=sample, status=200,
                      content_type='text/html')
        results = scraper.scrape(2)

        expected = ('6/4 Milson Road, Cremorne Point', 'Auction Sat 16 February - Guide $1,100,000',
                    '/property-apartment-nsw-cremorne+point-130285398')

        self.assertEqual(expected, results[0])


class IntegrationTestCase(unittest.TestCase):

    def setUp(self):
        self.session = Session()
        if not Association.__table__.exists(engine):
            Association.__table__.create(engine)

        if not RealEstate.__table__.exists(engine):
            RealEstate.__table__.create(engine)

    def tearDown(self):
        self.session.query(Association).delete()
        self.session.query(RealEstate).delete()
        self.session.commit()
        self.session.close()

    def test_noisy(self):
        result = calculations.near_noisy_transport(-33.843274, 151.211262)
        self.assertTrue(result)

        result = calculations.near_noisy_transport(-33.840966, 151.207475)
        self.assertTrue(result)

        result = calculations.near_noisy_transport(-33.844166, 151.229567)
        self.assertFalse(result)

        result = calculations.near_noisy_transport(-33.837466, 151.227521)
        self.assertFalse(result)

        result = calculations.near_noisy_transport(-33.834421, 151.220148)
        self.assertFalse(result)

        result = calculations.near_noisy_transport(-33.831030, 151.220389)
        self.assertTrue(result)

        result = calculations.near_noisy_transport(-33.84000, 151.22100)
        self.assertTrue(result)

    def test_get_catchment(self):
        result = calculations.get_catchment(-33.840823, 151.181776)
        expected = [{'catch_type': 'PRIMARY', 'gid': 1295, 'name': 'Greenwich PS'},
                    {'catch_type': 'HIGH_COED', 'gid': 393, 'name': 'Hunters Hill HS'}]
        self.assertEqual(expected, result)

    @responses.activate
    def test_geocode_catchment_commute(self):
        address = "9 Undercliff St, Neutral Bay NSW 2089"

        with open(r'data/geocode.json') as f:
            sample = f.read()

            responses.add(responses.GET, 'https://maps.googleapis.com/maps/api/geocode/json',
                          body=sample, status=200,
                          content_type='application/json')

        with open(r'data/directions.json') as f:
            sample = f.read()

            responses.add(responses.GET, 'https://maps.googleapis.com/maps/api/directions/json',
                          body=sample, status=200,
                          content_type='application/json')

        geom = calculations.geocode(address)
        lng, lat = geom['lng'], geom['lat']

        catchment = calculations.get_catchment(lat, lng)
        commute = calculations.transport_time_google(address)

        self.assertIsNotNone(catchment)
        expected = [{'catch_type': 'PRIMARY', 'gid': 1539, 'name': 'Neutral Bay PS'},
                    {'catch_type': 'HIGH_COED', 'gid': 1609, 'name': 'Mosman HS'}]
        self.assertEqual(expected, catchment)

        self.assertIsNotNone(commute)
        self.assertEqual(1271, commute)

    @responses.activate
    def test_enriched_records(self):
        with open(r'data/geocode.json') as f:
            sample = f.read()

            responses.add(responses.GET, 'https://maps.googleapis.com/maps/api/geocode/json',
                          body=sample, status=200,
                          content_type='application/json')

        with open(r'data/directions.json') as f:
            sample = f.read()

            responses.add(responses.GET, 'https://maps.googleapis.com/maps/api/directions/json',
                          body=sample, status=200,
                          content_type='application/json')

        result = scraper.enrich_records(RECORDS)
        self.assertTrue(result)
        self.assertEqual(6, len(result))

        expected = ['4/18 Spruson Street, Neutral Bay', 'Auction', '/property-apartment-nsw-neutral+bay-130266522',
                    False, 1271, [1539, 1609], 'POINT(151.2188275 -33.8378918)']
        self.assertEqual(expected, result[0])

    def test_filter_alerts(self):
        sample = [['4/18 Spruson Street, Neutral Bay', 'Auction', '/property-apartment-nsw-neutral+bay-130266522',
                   False, 1271, [1539, 1609], 'POINT(151.2188275 -33.8378918)'],
                  ['4/18 Spruson Street, Neutral Bay', 'Auction', '/property-apartment-nsw-neutral+bay-130266522',
                   False, 1234, [1234, 1609], 'POINT(151.2188275 -33.8378918)'],
                  ['4/18 Spruson Street, Neutral Bay', 'Auction', '/property-apartment-nsw-neutral+bay-130266522',
                   True, 1400, [1539, 1609], 'POINT(151.2188275 -33.8378918)'],
                  ['4/18 Spruson Street, Neutral Bay', 'Auction', '/property-apartment-nsw-neutral+bay-130266522',
                   False, 1800, [1539, 1609], 'POINT(151.2188275 -33.8378918)'],
                  ]

        result = [scraper.filter_alerts(sample)]

        self.assertEqual(1, len(result))

    @responses.activate
    def test_send(self):

        responses.add(responses.POST, 'https://api.pushover.net/1/messages.json',
                      status=201,
                      json={
                          'status': '1',
                          'request': '647d2300-702c-4b38-8b2f-d56326ae460b'
                      })

        result = scraper.send('Test Msg')

        self.assertEqual(201, result)

    @responses.activate
    def test_save(self):
        with open(r'data/geocode.json') as f:
            sample = f.read()

            responses.add(responses.GET, 'https://maps.googleapis.com/maps/api/geocode/json',
                          body=sample, status=200,
                          content_type='application/json')

        with open(r'data/directions.json') as f:
            sample = f.read()

            responses.add(responses.GET, 'https://maps.googleapis.com/maps/api/directions/json',
                          body=sample, status=200,
                          content_type='application/json')

        enriched = scraper.enrich_records(RECORDS)

        result = scraper.save(enriched)
        self.assertTrue(result)

        results = self.session.query(RealEstate).all()
        self.assertEqual(6, len(results))


if __name__ == '__main__':

    unittest.main()
