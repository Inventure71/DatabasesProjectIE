from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ProjectLayoutTests(SimpleTestCase):
    def test_repo_root_manage_py_is_the_django_entrypoint(self):
        repo_root = Path(settings.BASE_DIR).parent

        self.assertTrue((repo_root / "manage.py").exists())
        self.assertFalse((Path(settings.BASE_DIR) / "manage.py").exists())


class FrontendIntegrationTests(SimpleTestCase):
    def test_home_page_is_served_by_frontend_app(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

    def test_mock_catalog_cards_endpoint_returns_frontend_simulation_data(self):
        response = self.client.get("/mock-api/catalog/cards/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())
        self.assertGreater(len(response.json()["results"]), 0)
