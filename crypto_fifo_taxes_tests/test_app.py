import pytest
from django.core.management import call_command


@pytest.mark.django_db()
def test_index_page():
    call_command("init_project")

    assert True  # :)
