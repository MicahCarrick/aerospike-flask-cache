Aerospike Flask Cache Backend
=============================

[Aerospike](http://www.aerospike.com) is a low-latency distributed NoSQL database. This module provides a cache backend for [Flask-Caching](https://flask-caching.readthedocs.io/en/latest/index.html), the caching extension for [Flask](https://flask.palletsprojects.com/).

## Installation

Install the module with the following command:

```bash
pip install aerospike_flask_cache
```


## Set Up

```python
config = {
    'DEBUG': True,
    'CACHE_TYPE': "aerospike_flask.cache.aerospike.AerospikeCache",
    'CACHE_AEROSPIKE_HOSTS': [("172.17.0.2", 3000, None)],
    'CACHE_AEROSPIKE_NAMESPACE': "cache"
}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)
```

## Configuration Reference

| Configuration Value         | Description
|-----------------------------|-------------------------------------------------
| `CACHE_TYPE`                | `aerospike_flask.cache.aerospike.AerospikeCache`
| `CACHE_DEFAULT_TIMEOUT`     | The timeout (TTL) that is used if no other timeout is specified. Unit of time is seconds. Defaults to 300. 
| `CACHE_AEROSPIKE_CLIENT`    | Instantiated `aerospike.client` instance. One of `CACHE_AEROSPIKE_CLIENT` or `CACHE_AEROSPIKE_HOSTS` must be specified with `CACHE_AEROSPIKE_CLIENT` taking precedence.
| `CACHE_AEROSPIKE_HOSTS`     | Tuple of `(host, port, tls-name)` used to instantiate a `aerospike.client` object. One of `CACHE_AEROSPIKE_CLIENT` or `CACHE_AEROSPIKE_HOSTS` must be specified with `CACHE_AEROSPIKE_CLIENT` taking precedence.
| `CACHE_AEROSPIKE_NAMESPACE` | The name of the Aerospike namespace to store cached values. Defaults to `"cache"`.
| `CACHE_AEROSPIKE_SET`       | The name of the Aerospike set to store cached values. Defaults to `None` (Aerospike "null set").


## Logging

To enable DEBUG level logs for the `aerospike_flask.cache` module, set the level of the `aerospike_flask_cache` logger:

```python
from flask.logging import default_handler

logger = logging.getLogger('aerospike_flask_cache')
logger.setLevel(logging.DEBUG)
logger.addHandler(default_handler)
```

To enable DEBUG level logs for the `aerospike.client` module, add the default Flask handler to the aerospike module:

```python
from flask.logging import default_handler
import aerospike

aerospike.set_log_level(aerospike.LOG_LEVEL_DEBUG)
aerospike.set_log_handler(default_handler)
```

To enable DEBUG level logs when running tests use `--log-cli-level`:

```bash
pytest --log-cli-level=DEBUG
```


## Development

### Virtual Environment

Create a virtual environment with the desired version of Python (>= 3.8):

```bash
python -m venv .venv     
source .venv/bin/activate
```

Install the package as a symbolic link to enable editing the source code without re-installing:

```bash
pip install -e .
```

Print version to verify:

```bash
python -c "import aerospike_flask.cache; print(aerospike_flask.cache.__version__)"
```


### Testing

The tests can be run in 2 modes:

1. If the environment variable `AEROSPIKE_FLASK_CACHE_TEST_DB_HOST` is set the tests will be run against a live database.
2. If the environment variable `AEROSPIKE_FLASK_CACHE_TEST_DB_HOST` is NOT set tests will be run against a mock database.

For example, if Aerospike Database is running locally and listening on port 3000:

```bash
export AEROSPIKE_FLASK_CACHE_TEST_DB_HOST="127.0.0.1"
export AEROSPIKE_FLASK_CACHE_TEST_DB_PORT="3000"

pytest
```

__WARNING: Running tests against a live database will truncate the `testset` set in the `cachetest` namespace__

To instead run the tests with the mock Aerospike Database:

```bash
unset AEROSPIKE_FLASK_CACHE_TEST_DB_HOST

pytest
```

See [`examples/aerospike-pytest-docker`](examples/aerospike-pytest-docker/README.md) for an example of installing and configuring Aerospike Enterprise in Docker to be used with pytest.


### Linting

The Github Actions will run the `flake8` linter. Run it locally first to ensure the changes will pass:

```bash
flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=80 --statistics
```

## Troubleshooting

### Namespace supervisor (nsup) is disabled

By default Aerospike is not configured to run the "namespace supervisor (nsup). To use `timeout` (eg. `CACHE_DEFAULT_TIMEOUT=300`) then you ust set `nsup-period` to a non-zero value in the `aerospike.conf` file. See [nsup-period](https://aerospike.com/docs/server/reference/configuration#nsup-period) in the Aerospike documentation.

Failing to do so will result in the following error when using a `timeout` value other than `0` (never expires):

```
ERROR Failed to set TTL (timeout=X). Aerospike namespace supervisor (nsup) is disabled. Error 22: AEROSPIKE_ERR_FAIL_FORBIDDEN
```