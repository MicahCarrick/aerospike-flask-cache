Aerospike Flask Cache - PyTest Example
======================================

This is an example of installing and configuring Aerospike to run locally in a Docker container to be used when running the tests for `aerospike_flask.cache`.

Run [Aerospike Database Enterprise in Docker](https://aerospike.com/docs/deploy_guides/docker/). Aerospike Enterprise comes with a free developer license for single-node configuration which can be used for running tests.

```bash
sudo docker run -tid --name aerospike-server-pytest -p 3000:3000 \
-v "$(pwd)/opt":/opt/aerospike_flask_cache \
aerospike/aerospike-server-enterprise \
--config-file /opt/aerospike_flask_cache/aerospike.conf
```

__Note__: On Linux distributions with SELinux enabled you may need to append the `:Z` flag to the mount: `"$(pwd)/opt":/opt/aerospike_flask_cache:Z`

The IP address of the container can be obtained from `docker inspect`. Set the `AEROSPIKE_FLASK_CACHE_TEST_DB_HOST` environment variable to this IP address and the port that was mapped in the above Docker command:

```bash
export AEROSPIKE_FLASK_CACHE_TEST_DB_HOST="$(sudo docker inspect --format='{{.NetworkSettings.IPAddress}}')" aerospike-server-pytest
export AEROSPIKE_FLASK_CACHE_TEST_DB_HOST="3000"
```

