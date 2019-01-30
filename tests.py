import unittest
import responses
import calculations


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


class IntegrationTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

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
        expected = [{'catch_type': 'PRIMARY', 'name': 'Neutral Bay PS'},
                    {'catch_type': 'HIGH_COED', 'name': 'Mosman HS'}]
        self.assertEqual(expected, catchment)

        self.assertIsNotNone(commute)
        self.assertEqual(1271, commute)


if __name__ == '__main__':

    unittest.main()
