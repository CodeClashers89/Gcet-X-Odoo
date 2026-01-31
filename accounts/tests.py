from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache


@override_settings(
	CACHES={
		'default': {
			'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
		}
	}
)
class RateLimitTests(TestCase):
	def setUp(self):
		cache.clear()

	def test_login_rate_limit_exceeded(self):
		"""Login view should return 429 after max requests."""
		url = reverse('accounts:login')
		payload = {'email': 'noone@example.com', 'password': 'wrongpass'}

		# First 5 requests should not be rate limited
		for _ in range(5):
			response = self.client.post(url, data=payload)
			self.assertNotEqual(response.status_code, 429)

		# 6th request should be rate limited
		response = self.client.post(url, data=payload)
		self.assertEqual(response.status_code, 429)
