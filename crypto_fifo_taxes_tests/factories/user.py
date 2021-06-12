import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.LazyAttribute(lambda u: f"{u.first_name.lower()}_{ u.last_name.lower()}")
    email = factory.LazyAttribute(lambda u: f"{u.first_name.lower()}.{ u.last_name.lower()}@example.com")
