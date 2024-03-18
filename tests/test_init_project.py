import pytest
from django.core.management import call_command


@pytest.mark.django_db()
def test_init_project():
    call_command("init_project")

    assert True  # :)
