Aerospike Flask Cache Example
=============================

This is an example of a Flask application using the Aerospike Database as a backend for [Flask-Caching](https://flask-caching.readthedocs.io/en/latest/index.html).

Run [Aerospike Database Enterprise in Docker](https://aerospike.com/docs/deploy_guides/docker/). Aerospike Enterprise comes with a free developer license for single-node configuration which can be used to run this example.

```bash
sudo docker run -tid --name aerospike-server -p 3000:3000 \
-v "$(pwd)/opt":/opt/aerospike_flask_cache \
aerospike/aerospike-server-enterprise \
--config-file /opt/aerospike_flask_cache/aerospike.conf
```

__Note__: On Linux distributions with SELinux enabled you may need to append the `:Z` flag to the mount: `"$(pwd)/opt":/opt/aerospike_flask_cache:Z`

The file `opt/aerospike.conf` includes a [namespace configuration](https://aerospike.com/docs/server/operations/configure/namespace) for a namespace named `"cache"` that is suitable as an in-memory cache.

The IP address of the container can be obtained from `docker inspect`:

```bash
sudo docker inspect --format='{{.NetworkSettings.IPAddress}}' aerospike-community
```

This IP address and the Aerospike namespace `"cache"` are set in `example.py` as part of the Flask configuration:

```python
config = {
    'CACHE_TYPE': "aerospike_flask.cache.aerospike.AerospikeCache",
    'CACHE_AEROSPIKE_HOSTS': [("172.17.0.2", 3000, None)],
    'CACHE_AEROSPIKE_NAMESPACE': "cache"
}
```

Run the Flask development server:

```bash
flask run
```

See the routes defined in `example.py`. For example, navigating to `http://127.0.0.1:5000/template` will show a rendered template where the randomly generated number in the template block is cached for 60 seconds.
