from django.test import TestCase
from django.urls import reverse


class ApplicationHealthTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Household chores')

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('health-check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
