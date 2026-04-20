from django.db import models

from common.models import TimeStampedModel


class CardGame(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "card_game"
        ordering = ("name",)

    def __str__(self):
        return self.name


class CardSet(TimeStampedModel):
    game = models.ForeignKey(CardGame, on_delete=models.CASCADE, related_name="sets")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    release_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "card_set"
        ordering = ("game__name", "name")
        constraints = [
            models.UniqueConstraint(fields=("game", "code"), name="unique_set_code_per_game"),
        ]

    def __str__(self):
        return f"{self.game.name} - {self.name}"


class Card(TimeStampedModel):
    game = models.ForeignKey(CardGame, on_delete=models.CASCADE, related_name="cards")
    name = models.CharField(max_length=160)
    card_type = models.CharField(max_length=80, blank=True)
    subtype = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    artist_name = models.CharField(max_length=120, blank=True)
    attack = models.PositiveIntegerField(null=True, blank=True)
    defense = models.PositiveIntegerField(null=True, blank=True)
    hp = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "card"
        ordering = ("name",)
        indexes = [
            models.Index(fields=("name",), name="card_name_idx"),
            models.Index(fields=("game", "name"), name="card_game_name_idx"),
        ]

    def __str__(self):
        return self.name


class CardVariant(TimeStampedModel):
    class Rarity(models.TextChoices):
        COMMON = "COMMON", "Common"
        UNCOMMON = "UNCOMMON", "Uncommon"
        RARE = "RARE", "Rare"
        ULTRA_RARE = "ULTRA_RARE", "Ultra Rare"
        SECRET_RARE = "SECRET_RARE", "Secret Rare"
        PROMO = "PROMO", "Promo"

    class Finish(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        HOLO = "HOLO", "Holo"
        REVERSE_HOLO = "REVERSE_HOLO", "Reverse Holo"
        SHINY = "SHINY", "Shiny"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="variants")
    set = models.ForeignKey(CardSet, on_delete=models.CASCADE, related_name="variants")
    collector_number = models.CharField(max_length=40, blank=True)
    rarity = models.CharField(max_length=40, choices=Rarity.choices, default=Rarity.COMMON)
    finish = models.CharField(max_length=40, choices=Finish.choices, default=Finish.NORMAL)
    language = models.CharField(max_length=20, default="en")
    edition_label = models.CharField(max_length=80, blank=True)
    is_first_edition = models.BooleanField(default=False)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "card_variant"
        ordering = ("card__name", "set__name", "collector_number")
        indexes = [
            models.Index(fields=("set", "rarity"), name="variant_set_rarity_idx"),
            models.Index(fields=("current_value",), name="variant_value_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_value__gte=0),
                name="variant_current_value_non_negative",
            ),
            models.UniqueConstraint(
                fields=(
                    "card",
                    "set",
                    "collector_number",
                    "finish",
                    "language",
                    "edition_label",
                    "is_first_edition",
                ),
                name="unique_card_variant_printing",
            ),
        ]

    def __str__(self):
        return f"{self.card.name} ({self.set.name} {self.collector_number})"


class CardImage(TimeStampedModel):
    card_variant = models.OneToOneField(CardVariant, on_delete=models.CASCADE, related_name="image")
    image_url = models.URLField()
    image_hash = models.CharField(max_length=128, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "card_image"
        ordering = ("card_variant_id",)

    def __str__(self):
        return self.image_url
