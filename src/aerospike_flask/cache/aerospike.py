"""
    aerospike_flask.cache.aerospike
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Aerospike cache backend for Flask-Caching.

    :copyright: (c) 2024 by Micah Carrick.
    :license: BSD, see LICENSE for more details.
"""
# pylint: disable=no-member

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
        # pylint: disable=import-outside-toplevel
        try:
            import aerospike
            import aerospike_helpers.batch.records as aerospike_batch
            import aerospike_helpers.operations.operations as aerospike_ops
            cls._aerospike = aerospike
            cls._aerospike_batch = aerospike_batch
            cls._aerospike_ops = aerospike_ops
            logger.debug("Aerospike client version %s", aerospike.__version__)
        except ImportError as err:  # pragma: no cover
            raise RuntimeError("aerospike module not found") from err

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
        return self._put(key, value, timeout, False)

    def clear(self):
        """Clears the cache using the Aerospike 'truncate' info command.

        :returns: Whether the cache has been cleared.
        :rtype: boolean
        """
        logger.debug("Truncating %s.%s", self._namespace, self._set)
        # Note: truncate is async
        if self._client.truncate(self._namespace, self._set, 0) != 0:
            return False  # pragma: no cover

        return True

    def close_client(self):
        """Close client connections if the client is instantiated and
        connected. Called by `atexit` and/or when garbage collected.

        :returns: Returns ``True`` if the client connections were closed and
                 ``False`` if the client was not instantiated or was not
                 connected.
        :rtype: boolean
        """
        if self.is_connected():
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
        return self.inc(key, 0 - delta)

    def delete(self, key):
        """Delete `key` from the cache.

        :param key: the key to delete.
        :returns: Whether the key existed and has been deleted.
        :rtype: boolean
        """
        as_key = (self._namespace, self._set, key)

        (_, meta) = self._client.exists(as_key)
        if meta is None:
            return False
        self._client.remove(as_key)

        return True

    def delete_many(self, *keys):
        """Deletes multiple keys at once.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        :returns: A list containing all successfully deleted keys
        :rtype: boolean
        """
        as_keys = [(self._namespace, self._set, k) for k in keys]
        records = self._client.batch_remove(as_keys)
        r_val = [r.record[0][2] for r in records.batch_records if r.result == 0]

        return r_val

    def get(self, key):
        """Look up key in the cache and return the Aerospike bin value.

        :param key: the key to be looked up.
        :returns: The value if it exists and is readable, else ``None``.
        """
        try:
            as_key = (self._namespace, self._set, key)
            (_, _, r_value) = self._client.get(as_key)
            logger.debug("Cache hit on key: %s", key)
            return r_value[self._bin_name]
        except self._aerospike.exception.RecordNotFound:
            logger.debug("Cache miss on key: %s", key)
            return None

    def get_dict(self, *keys):
        """Like :meth:`get_many` but return a dict::

            d = cache.get_dict("foo", "bar")
            foo = d["foo"]
            bar = d["bar"]

        :param keys: The function accepts multiple keys as positional
                     arguments.
        """
        return dict(zip(keys, self.get_many(*keys)))

    def get_metadata(self, key):
        """Look up key in the cache and return the Aerospike record metadata.

        :param key: the key to be looked up.
        :returns: The metadata if the record exists, else ``None``.
        """
        try:
            as_key = (self._namespace, self._set, key)
            (_, r_meta, _) = self._client.get(as_key)
            return r_meta
        except self._aerospike.exception.RecordNotFound:
            return None

    def get_many(self, *keys):
        """Returns a list of values for the given keys using an Aerospike
        batch read operation.

        :param keys: The function accepts multiple keys as positional
                     arguments.
        :returns: list of values
        :rtype: list
        """
        as_keys = [(self._namespace, self._set, k) for k in keys]
        records = self._client.get_many(as_keys)
        r_val = []
        for record in records:
            bins = record[2]
            if bins is None:
                logger.debug("Cache miss on key: %s", record[0][2])
                r_val.append(None)
            else:
                logger.debug("Cache hit on key: %s", record[0][2])
                r_val.append(bins[self._bin_name])

        return r_val

    def _timeout_to_ttl_policies(self, timeout):
        """Get Aerospike TTL meta and policy for a given timeout.

        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: Tuple of 2 dictionaries for use with Aerospike methods:
                  ``(meta, policy)``
        :rtype: tuple
        """
        ttl = timeout

        if timeout is None:
            ttl = self.default_timeout
        elif timeout == 0:
            ttl = self._aerospike.TTL_NEVER_EXPIRE

        meta = {'ttl': ttl}
        policy = {}
        if timeout != 0:
            policy['ttl'] = ttl

        return meta, policy

    def has(self, key):
        """Checks if a key exists in the cache without returning it. This is a
        cheap operation that bypasses loading the actual data on the backend.

        :param key: the key to check
        :returns: ``True`` if the key exists, ``False`` if it does not
        :rtype: boolean
        """
        as_key = (self._namespace, self._set, key)
        (_, meta) = self._client.exists(as_key)
        if meta is None:
            return False

        return True

    def inc(self, key, delta=1):
        """Increments the value of a key by `delta`.  If the key does
        not yet exist it is initialized with `delta`.

        For supporting caches this is an atomic operation.

        :param key: the key to increment.
        :param delta: the delta to add.
        :returns: The new value or ``None`` for backend errors.
        """
        as_key = (self._namespace, self._set, key)

        if self.has(key):
            ops = [
                self._aerospike_ops.increment(self._bin_name, delta),
                self._aerospike_ops.read(self._bin_name)
            ]
        else:
            ops = [
                self._aerospike_ops.write(self._bin_name, delta),
                self._aerospike_ops.read(self._bin_name)
            ]

        try:
            (_, _, bins) = self._client.operate(as_key, ops)
        except self._aerospike.exception.ParamError as err:
            logger.error("Error %s: %s", err.code, err.msg)
            return None

        return bins[self._bin_name]

    def is_connected(self):
        """Check if the Aerospike client is initialized and connected to the
        database.

        :returns: ``True`` if the Aerospike client is connected
        :rtype: boolean
        """
        if self._client is not None and self._client.is_connected():
            return True

        return False

    def _log_aerospike_error(self, err):
        """Log a detailed message about
        """
        if isinstance(err, self._aerospike.exception.ForbiddenError):
            msg = "Failed to set TTL. Aerospike namespace supervisor " + \
                  "(nsup) may be disabled. Error %s: %s"
            logger.error(msg, err.code, err.msg)
        else:
            logger.error("Error %s: %s", err.code, err.msg)

    def _put(self, key, value, timeout=None, replace=True):
        """Save a value in Aerospike using the single-record put operations.

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        "param replace: whether or not the record should be replaced if it
                        already exists
        :returns: ``True`` if key has been updated, ``False`` for backend
                  errors.
        :rtype: boolean
        """
        meta, policy = self._timeout_to_ttl_policies(timeout)

        if replace:
            policy['exists'] = self._aerospike.POLICY_EXISTS_CREATE_OR_REPLACE
        else:
            policy['exists'] = self._aerospike.POLICY_EXISTS_CREATE

        as_key = (self._namespace, self._set, key)

        try:
            self._client.put(as_key, {self._bin_name: value}, meta, policy)
        except self._aerospike.exception.AerospikeError as err:
            self._log_aerospike_error(err)
            return False

        return True

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
        return self._put(key, value, timeout, True)

    def set_many(self, mapping, timeout=None):
        """Sets multiple keys and values from a mapping.

        :param mapping: a mapping with the keys/values to set.
        :param timeout: the cache timeout for the key in seconds (if not
                        specified, it uses the default timeout). A timeout of
                        0 indicates that the cache never expires.
        :returns: A list containing all keys successfully set
        :rtype: list
        """
        meta, policy = self._timeout_to_ttl_policies(timeout)
        as_keys = [(self._namespace, self._set, k) for k in mapping.keys()]
        batch = []

        for k in as_keys:
            batch.append(
                self._aerospike_batch.Write(
                    key=k,
                    ops=[
                        self._aerospike_ops.write(self._bin_name, mapping[k[2]])
                    ],
                    meta=meta
                )
            )

        batch_records = self._aerospike_batch.BatchRecords(batch)
        self._client.batch_write(batch_records, policy)

        r_list = []
        for br in batch_records.batch_records:
            if br.result == 0:
                r_list.append(br.record[0][2])

        return r_list
