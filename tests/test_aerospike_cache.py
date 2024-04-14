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

import aerospike

from aerospike_flask import cache
from aerospike_flask.cache.aerospike import AerospikeCache


class TestModule:
    """Tests for Python module functionality
    """
    def test_version(self):
        """get version returns version as a semver string
        """
        assert isinstance(cache.get_version(), str)
        assert cache.get_version() == cache.__version__


class CacheTestsBase:
    """Base class for all tests
    """
    @pytest.fixture
    def c(self):
        """return a cache instance
        """
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
        yield c


class TestBaseCache(CacheTestsBase):
    """Tests for methods defined in flask_caching.backends.base.BaseCache
    (cachelib.base.BaseCache)
    """
    def test_add(self, c):
        """add method does not replace the value if it exists
        """
        assert c.add("k1", "v1")
        assert c.add("k1", "v2") is False
        assert c.get("k1") == "v1"

    def test_set(self, c):
        """set method always replaces the value
        """
        assert c.set("k1", "v1")
        assert c.set("k1", "v2")
        assert c.get("k1") == "v2"

    def test_get(self, c):
        """get method returns value or None if not found
        """
        assert c.set("k1", "v1")
        v1 = c.get("k1")
        assert v1 == "v1"
        v2 = c.get("k2")
        assert v2 is None


class TestAerospikeCache(CacheTestsBase):
    """Tests for Aerospike specific functionality
    """
    def test_initialize_with_client(self):
        """cache can be initialized with existing `aerospike.client` object
        """
        # Note: initializing with just the host string is already covered by
        # the fixture in CacheTestsBase used in most other test cases
        asconfig = [(
                getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_HOST"),
                int(getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_PORT", "3000")),
                getenv("AEROSPIKE_FLASK_CACHE_TEST_DB_TLS_NAME")
            )]
        # pylint: disable=no-member
        client = aerospike.client({'hosts': asconfig}).connect()
        config = {
            'CACHE_AEROSPIKE_CLIENT': client,
            'CACHE_AEROSPIKE_NAMESPACE': "cachetest",
        }
        c = AerospikeCache.factory(None, config, [], {})
        c.close_client()
        c = None

    def test_invalid_config(self):
        """missing required configuration raises runtime exceptions
        """
        # missing CACHE_AEROSPIKE_HOSTS and CACHE_AEROSPIKE_CLIENT
        with pytest.raises(RuntimeError):
            config = {
                'CACHE_AEROSPIKE_NAMESPACE': 'foo',
                'CACHE_AEROSPIKE_SET': 'foo'
            }
            _ = AerospikeCache.factory(None, config, [], {})

        # missing CACHE_AEROSPIKE_NAMESPACE
        with pytest.raises(RuntimeError):
            config = {
                'CACHE_AEROSPIKE_HOSTS': [('foo.bar', 3000)]
            }
            _ = AerospikeCache.factory(None, config, [], {})

        # CACHE_AEROSPIKE_NAMESPACE exceeds 31 characters
        with pytest.raises(RuntimeError):
            config = {
                'CACHE_AEROSPIKE_HOSTS': [('foo.bar', 3000)],
                'CACHE_AEROSPIKE_NAMESPACE': 'x' * 32
            }
            _ = AerospikeCache.factory(None, config, [], {})

        # CACHE_AEROSPIKE_NAMESPACE exceeds 31 characters
        with pytest.raises(RuntimeError):
            config = {
                'CACHE_AEROSPIKE_HOSTS': [('foo.bar', 3000)],
                'CACHE_AEROSPIKE_NAMESPACE': 'foo',
                'CACHE_AEROSPIKE_SET': 'x' * 64
            }
            _ = AerospikeCache.factory(None, config, [], {})

    def test_set_with_ttl(self, c, monkeypatch):
        """get with timeout should set Aerospike TTL
        """
        # pylint: disable=missing-class-docstring,missing-function-docstring
        # pylint: disable=no-member,too-few-public-methods

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

        # ForbiddenError is caught and returns False
        class MockForbiddenErrorClient():
            def put(self, key, bins=None, meta=None, policy=None):
                raise aerospike.exception.ForbiddenError

        monkeypatch.setattr(c, '_client', MockForbiddenErrorClient)
        assert c.set("k1", "v1") is False

        # AerospikeError is caught and returns False
        class MockAerospikeErrorClient():
            def put(self, key, bins=None, meta=None, policy=None):
                raise aerospike.exception.AerospikeError

        monkeypatch.setattr(c, '_client', MockAerospikeErrorClient)
        assert c.set("k1", "v1") is False

        # Unknown exceptions are not caught
        # pylint: disable=broad-exception-raised
        class MockExceptionClient():
            def put(self, key, bins=None, meta=None, policy=None):
                raise Exception
        monkeypatch.setattr(c, '_client', MockExceptionClient)
        with pytest.raises(Exception):
            c.set("k1", "v1")

    def test_get_metadata(self, c):
        """get metadata should return metadata object or ``None`` if the
        record is not found
        """
        c.set("k1", "v1")
        meta = c.get_metadata("k1")
        assert 'ttl' in meta
        assert 'gen' in meta

        assert c.get_metadata("foo") is None

    def test_client_cleanup(self, c):
        """finalize method should close Aerospike client connections
        """
        # pylint: disable=unnecessary-dunder-call
        assert c.is_connected() is True
        c.__del__()
        assert c.is_connected() is False

    def test_client_double_close(self, c):
        """closing Aerospike client connections that have already been closed
        should return ``False``
        """
        assert c.close_client() is True
        assert c.close_client() is False
