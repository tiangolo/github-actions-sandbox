from app.utils import get_name


def test_get_name():
    assert get_name() == "World"
