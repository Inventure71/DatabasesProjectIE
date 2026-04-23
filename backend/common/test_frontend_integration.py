from pathlib import Path
from decimal import Decimal

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from catalog.models import Card, CardGame, CardSet, CardVariant


class ProjectLayoutTests(SimpleTestCase):
    def test_repo_root_manage_py_is_the_django_entrypoint(self):
        repo_root = Path(settings.BASE_DIR).parent

        self.assertTrue((repo_root / "manage.py").exists())
        self.assertFalse((Path(settings.BASE_DIR) / "manage.py").exists())


class FrontendIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        game = CardGame.objects.create(name="Frontend Integration", slug="frontend-integration")
        card_set = CardSet.objects.create(game=game, name="Integration Set", code="INT")
        card = Card.objects.create(game=game, name="Integration Dragon")
        CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="1/1",
            rarity=CardVariant.Rarity.RARE,
            current_value=Decimal("10.00"),
        )

    def test_home_page_is_served_by_frontend_app(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integration Dragon")

    def test_mock_api_is_not_mounted(self):
        response = self.client.get("/mock-api/catalog/cards/")

        self.assertEqual(response.status_code, 404)
