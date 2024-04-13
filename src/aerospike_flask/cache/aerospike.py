"""
    aerospike_flask.cache.aerospike
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Aerospike cache backend for Flask-Caching.

    :copyright: (c) 2024 by Micah Carrick.
    :license: BSD, see LICENSE for more details.
"""

import logging
import atexit

from flask_caching.backends.base import BaseCache

logger = logging.getLogger('aerospike_flask_cache')


class AerospikeCache(BaseCache):
    """Cache backend using Aerospike Database as a distributed cache

    :param client: instantiated aerospike.client instance
    :param namespace: Aerospike namespace name
    :param set_name: Aerospike set name or the "null set" if ``None``
    :param default_timeout: default timeout (TTL) in seconds
    """

    def __init__(self, client, namespace, set_name=None, default_timeout=300):
        BaseCache.__init__(self, default_timeout=default_timeout)
        client.connect()
        self._client = client
        self._namespace = namespace
        self._set = set_name
        self._bin_name = "v"
        self.default_timeout = default_timeout

        atexit.register(self.close_client)

    @classmethod
    def factory(cls, app, config, args, kwargs):
        # pylint: disable=import-outside-toplevel,no-member
        try:
            import aerospike
            cls._aerospike = aerospike
            logger.debug("Aerospike client version %s", aerospike.__version__)
        except ImportError as err:
            raise RuntimeError("aerospike module not found") from err

        # instantiated client takes precedence over hosts array
        if "CACHE_AEROSPIKE_CLIENT" in config:
            kwargs["client"] = config.get("CACHE_AEROSPIKE_CLIENT", None)
        elif "CACHE_AEROSPIKE_HOSTS" in config:
            asconf = {
                'hosts': config.get("CACHE_AEROSPIKE_HOSTS")
            }
            kwargs["client"] = aerospike.client(asconf)
            logger.debug("Initialized client: %s", kwargs["client"])
        else:
            raise RuntimeError("must specify client or host")

        if 'CACHE_AEROSPIKE_NAMESPACE' not in config:
            msg = "CACHE_AEROSPIKE_NAMESPACE is required"
            raise RuntimeError(msg)

        kwargs['namespace'] = config.get("CACHE_AEROSPIKE_NAMESPACE", "cache")
        kwargs['set_name'] = config.get("CACHE_AEROSPIKE_SET", None)

        if len(kwargs['namespace'].encode('utf-8')) > 31:
            msg = "CACHE_AEROSPIKE_NAMESPACE must be less than 32 characters"
            raise RuntimeError(msg)

        if kwargs['set_name'] and len(kwargs['set_name'].encode('utf-8')) > 63:
            msg = "CACHE_AEROSPIKE_SET must be less than 64 characters"
            raise RuntimeError(msg)

        return cls(*args, **kwargs)

    def __del__(self):
        """ Close client connections when garbage collected.
        """
        self.close_client()

    def add(self, key, value, timeout=None):
        """Works like :meth:`set` but does not overwrite the values of already
        existing keys.

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: Same as :meth:`set`, but also ``False`` for already
                  existing keys.
        :rtype: boolean
        """
        # TODO: not implemented
        return True

    def clear(self):
        """Clears the cache using the Aerospike 'truncate' info command.

        :returns: Whether the cache has been cleared.
        :rtype: boolean
        """
        if self._client.truncate(self._namespace, self._set, 0) != 0:
            return False

        return False

    def close_client(self):
        """Close client connections if the client is instantiated and
        connected. Called by `atexit` and/or when garbage collected.

        :returns: Returns ``True`` if the client connections were closed and
                 ``False`` if the client was not instantiated or was not
                 connected.
        :rtype: boolean
        """
        if self._client is not None and self._client.is_connected():
            logger.debug("closing Aerospike client: %s", self._client)
            self._client.close()
            self._client = None
            return True

        return False

    def dec(self, key: str, delta=1):
        """Decrements the value of a key by `delta`.  If the key does
        not yet exist it is initialized with `-delta`.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to subtract.
        :returns: The new value or `None` for backend errors.
        """
        # TODO: not implemented
        value = (self.get(key) or 0) - delta
        return value if self.set(key, value) else None

    def delete(self, key):
        """Delete `key` from the cache.

        :param key: the key to delete.
        :returns: Whether the key existed and has been deleted.
        :rtype: boolean
        """
        # TODO: not implemented
        return True

    def delete_many(self, *keys):
        """Deletes multiple keys at once.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        :returns: A list containing all successfully deleted keys
        :rtype: boolean
        """
        # TODO: not implemented
        deleted_keys = []
        for key in keys:
            if self.delete(key):
                deleted_keys.append(key)
        return deleted_keys

    def has(self, key):
        """Checks if a key exists in the cache without returning it. This is a
        cheap operation that bypasses loading the actual data on the backend.

        :param key: the key to check
        """
        # TODO: not implemented
        raise NotImplementedError(
            "%s doesn't have an efficient implementation of `has`. That "
            "means it is impossible to check whether a key exists without "
            "fully loading the key's data. Consider using `self.get` "
            "explicitly if you don't care about performance."
        )

    def inc(self, key, delta=1):
        """Increments the value of a key by `delta`.  If the key does
        not yet exist it is initialized with `delta`.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to add.
        :returns: The new value or ``None`` for backend errors.
        """
        # TODO: not implemented
        value = (self.get(key) or 0) + delta
        return value if self.set(key, value) else None

    def get(self, key):
        """Look up key in the cache and return the Aerospike bin value.

        :param key: the key to be looked up.
        :returns: The value if it exists and is readable, else ``None``.
        """
        # pylint: disable=no-member
        try:
            as_key = (self._namespace, self._set, key)
            (_, _, r_value) = self._client.get(as_key)
            logger.debug("Cache hit on key: %s", key)
            return r_value[self._bin_name]
        except self._aerospike.exception.RecordNotFound:
            logger.debug("Cache miss on key: %s", key)
            return None

    def get_metadata(self, key):
        """Look up key in the cache and return the Aerospike record metadata.

        :param key: the key to be looked up.
        :returns: The metadata if the record exists, else ``None``.
        """
        # pylint: disable=no-member
        try:
            as_key = (self._namespace, self._set, key)
            (_, r_meta, _) = self._client.get(as_key)
            return r_meta
        except self._aerospike.exception.RecordNotFound:
            return None

    def get_many(self, *keys):
        """Returns a list of values for the given keys.
        For each key an item in the list is created::

            foo, bar = cache.get_many("foo", "bar")

        Has the same error handling as :meth:`get`.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        """
        # TODO: not implemented
        return [self.get(k) for k in keys]

    def get_dict(self, *keys):
        """Like :meth:`get_many` but return a dict::

            d = cache.get_dict("foo", "bar")
            foo = d["foo"]
            bar = d["bar"]

        :param keys: The function accepts multiple keys as positional
                     arguments.
        """
        # TODO: not implemented
        return dict(zip(keys, self.get_many(*keys)))  # noqa: B905

    def set(self, key, value, timeout=None):
        """Add a new key/value to the cache (overwrites value, if key already
        exists in the cache).

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: ``True`` if key has been updated, ``False`` for backend
                  errors.
        :rtype: boolean
        """
        # pylint: disable=no-member
        if timeout is None:
            timeout = self.default_timeout
        if timeout == 0:
            meta = {'ttl': self._aerospike.TTL_NEVER_EXPIRE}
            policy = {}
        else:
            meta = {'ttl': timeout}
            policy = {'ttl': timeout}

        as_key = (self._namespace, self._set, key)

        try:
            self._client.put(as_key, {self._bin_name: value}, meta, policy)
        except self._aerospike.exception.ForbiddenError as err:
            msg = f"Failed to set TTL (timeout={timeout}). " + \
                  "Aerospike namespace supervisor (nsup) is disabled. " + \
                  f"Error {err.code}: {err.msg}"
            logger.error(msg)
            return False
        except self._aerospike.exception.AerospikeError as err:
            logger.error("Error %s: %s", err.code, err.msg)
            return False

        return True

    def set_many(self, mapping, timeout=None):
        """Sets multiple keys and values from a mapping.

        :param mapping: a mapping with the keys/values to set.
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: A list containing all keys successfully set
        :rtype: boolean
        """
        # TODO: not implemented
        set_keys = []
        for key, value in mapping.items():
            if self.set(key, value, timeout):
                set_keys.append(key)
        return set_keys

