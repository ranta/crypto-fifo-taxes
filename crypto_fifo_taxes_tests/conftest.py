import pytest


@pytest.fixture(autouse=True)
def clear_cache_between_tests(db):
    # Clear Django's cache
    from django.core.cache import cache

    cache.clear()

    # Clear all LRU method caches
    # refs. https://stackoverflow.com/a/50699209
    import functools
    import gc

    gc.collect()
    wrappers = [a for a in gc.get_objects() if isinstance(a, functools._lru_cache_wrapper)]
    for wrapper in wrappers:
        wrapper.cache_clear()
