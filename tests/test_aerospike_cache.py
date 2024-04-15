"""
    tests/test_aerospike_cache.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests for the aerospike_flask.cache module.

    :copyright: (c) 2024 by Micah Carrick.
    :license: BSD, see LICENSE for more details.
"""
# pylint: disable=no-member,unused-argument

from os import getenv
from time import sleep
from uuid import uuid4

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
        sleep(1)  # allow time for truncate
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

    def test_clear(self, c):
        """clear issues a trucate which asychronously deletes all records
        """
        c.set("k1", "v1")
        assert c.clear() is True

    def test_delete(self, c):
        """delete returns True if the value was deleted and False if it did
        not exist and/or was not deleted
        """
        key = str(uuid4())
        assert c.delete(key) is False
        c.set(key, "v1")
        assert c.get(key) is not None
        assert c.delete(key) is True
        assert c.get(key) is None

    def test_delete_many(self, c):
        """delete many should return a list of all the keys that were deleted
        """
        key1 = str(uuid4())
        key2 = str(uuid4())
        key3 = str(uuid4())
        c.set_many({key1: "v1", key2: "v2"})
        assert c.delete_many(key1, key2) == [key1, key2]
        assert c.get_many(key1, key2) == [None, None]

        c.set_many({key1: "v1", key2: "v2"})
        assert c.delete_many(key1, key2, key3) == [key1, key2]
        assert c.get_many(key1, key2) == [None, None]

    def test_get(self, c):
        """get method returns value or None if not found
        """
        assert c.set("k1", "v1")
        v1 = c.get("k1")
        assert v1 == "v1"
        v2 = c.get("k2")
        assert v2 is None

    def test_get_dict(self, c):
        """get_dict gets all the values but returns a dict of key/value pairs
        rather than just a list of values
        """
        assert c.get_dict("k1", "k2") == {"k1": None, "k2": None}
        keys = c.set_many({"k1": "v1", "k2": "v2"})
        values = c.get_dict(*keys)
        assert values == {"k1": "v1", "k2": "v2"}

    def test_get_many(self, c):
        """get_many gets value for all keys and ``None`` for keys that don't
        exist
        """
        assert c.get_many("k1", "k2") == [None, None]
        keys = c.set_many({"k1": "v1", "k2": "v2"})
        values = c.get_many(*keys)
        assert isinstance(values, list)
        assert values == ["v1", "v2"]
        values = c.get_many("k2", "foo", "k1")
        assert values == ["v2", None, "v1"]

    def test_has(self, c):
        """has returns ``True`` when the key exists and ``False`` when it
        does not
        """
        c.set("k1", "v1")
        assert c.has("k1") is True
        assert c.has("k2") is False

    def test_inc(self, c):
        """inc method should increment the value or set it if the record
        doesn't already exist
        """
        key = str(uuid4())
        assert c.inc(key, 10) == 10
        assert c.inc(key, 5) == 15

        # backend error returns None
        assert c.inc(key, "foo") is None

    def test_dec(self, c):
        """dec method should decrement the value or set it if the record
        doesn't already exist
        """
        assert c.dec("k1", 10) == -10
        assert c.dec("k1", 5) == -15

        # backend error returns None
        assert c.inc("k1", "foo") is None

    def test_set(self, c):
        """set method always replaces the value
        """
        assert c.set("k1", "v1")
        assert c.set("k1", "v2")
        assert c.get("k1") == "v2"

    def test_set_many(self, c):
        """set_many replaces all values in mapping and returns list of keys
        successfully set
        """
        c.set("k1", "value_to_replace")
        r = c.set_many({"k1": "v1", "k2": "v2"})
        assert isinstance(r, list)
        assert "k1" in r
        assert c.get("k1") == "v1"
        assert "k2" in r
        assert c.get("k2") == "v2"


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

    def test_timeout_ttl(self, c, monkeypatch):
        """all methods that write records set timeout as Aerospike TTL
        """
        # pylint: disable=missing-class-docstring,missing-function-docstring
        # pylint: disable=too-few-public-methods
        timeout_to_ttl = (
            (0, -1 & 0xffffffff),  # A tiemout of 0 TTL (never expire)
            (123, 123),  # non-zero, non-null value sets TTL to timeout
            (None, 300)  # default
        )

        for t in timeout_to_ttl:
            # timeout results in correct Aerospike TTL
            timeout, ttl = t

            key = str(uuid4())
            assert c.set(key, "v1", timeout=timeout) is True
            meta = c.get_metadata(key)
            assert meta['ttl'] == ttl

            key = str(uuid4())
            assert c.add(key, "v1", timeout=timeout) is True
            meta = c.get_metadata(key)
            assert meta['ttl'] == ttl

            key1 = str(uuid4())
            key2 = str(uuid4())
            c.set_many({key1: "v1", key2: "v2"}, timeout=timeout)
            assert c.get_metadata(key1)['ttl'] == ttl
            assert c.get_metadata(key2)['ttl'] == ttl

        # timeout removes record from cache
        key = str(uuid4())
        c.set(key, "v2", timeout=1)
        assert c.get(key) == "v2"
        sleep(2)
        assert c.get(key) is None

        key = str(uuid4())
        c.add(key, "v2", timeout=1)
        assert c.get(key) == "v2"
        sleep(2)
        assert c.get(key) is None

        key1 = str(uuid4())
        key2 = str(uuid4())
        c.set_many({key1: "v1", key2: "v2"}, timeout=1)
        assert c.get(key1) == "v1"
        assert c.get(key2) == "v2"
        sleep(2)
        assert c.get(key1) is None
        assert c.get(key2) is None

        # ForbiddenError is caught and returns False
        class MockForbiddenErrorClient():
            def put(self, key, bins=None, meta=None, policy=None):
                e = aerospike.exception.ForbiddenError
                e.code = 22
                e.msg = "this is a test mock"
                raise e

        monkeypatch.setattr(c, '_client', MockForbiddenErrorClient)
        assert c.set("k1", "v1") is False

        # AerospikeError is caught and returns False
        class MockAerospikeErrorClient():
            def put(self, key, bins=None, meta=None, policy=None):
                e = aerospike.exception.AerospikeError
                e.code = -1
                e.msg = "this is a test mock"
                raise e

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
