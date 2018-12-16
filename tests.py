import unittest
import responses
from calculations import transport_time


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
        result = transport_time('-33.846206', '151.229796')
        self.assertEqual(38.2, result)


if __name__ == '__main__':

    unittest.main()
