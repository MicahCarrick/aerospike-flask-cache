"""
    tests/test_aerospike_cache.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for the aerospike_flask.cache module.

    :copyright: (c) 2024 by Micah Carrick.
    :license: BSD, see LICENSE for more details.
"""

from os import getenv
from time import sleep

import pytest

from aerospike_flask.cache.aerospike import AerospikeCache


class MockAerospikeClient:
    """ Mock Aerospike client for testing without live database
    """
    def __init__(self):
        self._cache = {}

    def close(self):
        """ Mock close method
        """

    def is_connected(self):
        """ Mock is_connected by always returning True
        """
        return True

    def truncate(self, namespace=None, set=None, nanos=0, policy=None):
        """ Mock truncate by always returning 0
        """
        return 0


class CacheTestsBase:
    """Base class for all tests
    """
    @pytest.fixture
    def c(self):
        """Return a cache instance."""
        if getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_HOST") is not None:
            config = {
                'CACHE_AEROSPIKE_HOSTS': [(
                    getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_HOST"),
                    int(getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_PORT", "3000")),
                    getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_TLS_NAME")
                )],
                'CACHE_AEROSPIKE_NAMESPACE': "cachetest",
                'CACHE_AEROSPIKE_SET': "testset"
            }
            c = AerospikeCache.factory(None, config, [], {})
            c.clear()
        else:
            c = AerospikeCache(MockAerospikeClient(), "testcache", "testset")
            c.clear()
        yield c


class TestBaseCache(CacheTestsBase):
    """ Tests for methods defined in flask_caching.backends.base.BaseCache
    (cachelib.base.BaseCache)
    """
    def test_set(self, c):
        """ set method persists the value
        """
        assert c.set("k1", "v1")

    def test_get(self, c):
        """ get method returns value or None if not found
        """
        assert c.set("k1", "v1")
        v1 = c.get("k1")
        assert v1 == "v1"
        v2 = c.get("k2")
        assert v2 is None

    #def test_get_dict(self, c):
    #    c.set("k", "v")
    #    d = c.get_dict("k")
    #    assert "a" in d
    #    assert "foo" == d["a"]

class TestAerospikeCache(CacheTestsBase):
    """Tests for Aerospike specific functionality
    """
    def test_set_with_ttl(self, c):
        """ get with timeout should set Aerospike TTL
        """
        # TODO: mock a ForbiddenError (nsup not enabled)?
        # 1 second TTL
        c.set("k1", "v1", timeout=1)
        assert c.get("k1") == "v1"
        meta = c.get_metadata("k1")
        assert meta['ttl'] == 1
        sleep(2)
        assert c.get("k1") is None

        # 0 TTL (never expire)
        c.set("k2", "v2", timeout=0)
        meta = c.get_metadata("k2")
        assert meta['ttl'] == -1 & 0xffffffff
