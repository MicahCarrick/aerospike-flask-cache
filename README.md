Aerospike Flask Cache Backend
=============================

[![Aerospike 7](https://img.shields.io/badge/Aerospike-v7.0+-C22127?labelColor=white&logo=aerospike&logoColor=C22127&style=flat)](http://www.aerospike.com)
[![Aerospike Enterprise](https://img.shields.io/badge/Aerospike-Enterprise_Editition-C22127?labelColor=white&logo=aerospike&logoColor=C22127&style=flat)](https://aerospike.com/download/#aerospike-server-enterprise-edition)
[![Aerospike Community](https://img.shields.io/badge/Aerospike-Community_Editition-C22127?labelColor=white&logo=aerospike&logoColor=C22127&style=flat)](https://aerospike.com/download/#aerospike-server-community-edition)


[![Tests](https://github.com/MicahCarrick/aerospike-flask-cache/actions/workflows/tests.yml/badge.svg)](https://github.com/MicahCarrick/aerospike-flask-cache/actions/workflows/tests.yml)
[![Build](https://github.com/MicahCarrick/aerospike-flask-cache/actions/workflows/build.yml/badge.svg)](https://github.com/MicahCarrick/aerospike-flask-cache/actions/workflows/build.yml)



[Aerospike](http://www.aerospike.com) is a low-latency distributed NoSQL database. This module provides a cache backend for [Flask-Caching](https://flask-caching.readthedocs.io/en/latest/index.html), the caching extension for [Flask](https://flask.palletsprojects.com/).

Questions, comments, feedback? Find me in the `#ask-the-community` channel in the [Aerospike Developer Discord server](https://discord.com/invite/NfC93wJEJU).

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
| `CACHE_AEROSPIKE_HOSTS`     | List of tuples of `(host, port, tls-name)` used to instantiate a `aerospike.client` object. One of `CACHE_AEROSPIKE_CLIENT` or `CACHE_AEROSPIKE_HOSTS` must be specified with `CACHE_AEROSPIKE_CLIENT` taking precedence.
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

Create a virtual environment with the desired version of Python:

```bash
python -m venv .venv     
source .venv/bin/activate
```

Install the package as a symbolic link to enable editing of the source code without re-installing the package:

```bash
pip install -e .
```

Print version to verify:

```bash
python -c "import aerospike_flask.cache; print(aerospike_flask.cache.__version__)"
```


### Testing

The tests are run with a Github Action on push or pull request to `dev` and `main` branches. Tests should pass locally first.

The tests are run against a running Aerospike Database server. The host and port of a seed node of the test server are set with environment variables:

```bash
export AEROSPIKE_FLASK_CACHE_TEST_DB_HOST="127.0.0.1"
export AEROSPIKE_FLASK_CACHE_TEST_DB_PORT="3000"

pytest
```
__WARNING: Running tests against a live database will truncate the `testset` set in the `cachetest` namespace__

For local testing you can run [Aerospike Database Enterprise in Docker](https://aerospike.com/docs/deploy_guides/docker/). Aerospike Enterprise comes with a free developer license for single-node configuration which can be used for running tests.

The following command will run Aerospike Database Enterprise using the free developer license in a container listening on port `3999`.

```bash
docker run -tid --name aerospike-server-pytest -p 3999:3000 \
-v "$(pwd)/tests/opt":/opt/aerospike_flask_cache \
aerospike/aerospike-server-enterprise \
--config-file /opt/aerospike_flask_cache/aerospike.conf
```

__Note__: On Linux distributions with SELinux enabled you may need to append the `:Z` flag to the mount: `"$(pwd)/opt":/opt/aerospike_flask_cache:Z`

The IP address of the container can be obtained from `docker inspect`. Set the `AEROSPIKE_FLASK_CACHE_TEST_DB_HOST` environment variable to this IP address and the port that was mapped in the above Docker command:

```bash
export AEROSPIKE_FLASK_CACHE_TEST_DB_HOST="$(docker inspect --format='{{.NetworkSettings.IPAddress}}' aerospike-server-pytest)"
export AEROSPIKE_FLASK_CACHE_TEST_DB_PORT="$(docker inspect --format='{{(index (index .NetworkSettings.Ports "3000/tcp") 0).HostPort}}' aerospike-server-pytest)"
```

To view test coverage run:

```
pytest --cov=aerospike_flask.cache tests/ --cov-report term-missing
```


### Linting

Source code is checked with a Github Action using the `flake8` linter. Run it locally first to ensure any changes will pass:

```bash
flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=80 --statistics
```

### Building

Packages are built with a Github Action on push or pull request into the `dev` and `main` branches.

Manually build Python packages (`sdist` and `wheel`) using hatch:

```
hatch build
```

### Publishing to TestPyPI

Packages are published to TestPyPI with a Github Action when pushed or merged into the `dev` branch.

### Publishing to Github and PyPI

Packages are published to PyPI with a Github Action when version tags are pushed.

To push a version tag:

```
VERSION="$(python -c 'import aerospike_flask.cache; print(aerospike_flask.cache.__version__)')"; git tag -a -m $VERSION $VERSION
git push --tags
```

## Troubleshooting

### Namespace supervisor (nsup) is disabled

By default Aerospike is not configured to run the "namespace supervisor (nsup). To use `timeout` (eg. `CACHE_DEFAULT_TIMEOUT=300`) then you ust set `nsup-period` to a non-zero value in the `aerospike.conf` file. See [nsup-period](https://aerospike.com/docs/server/reference/configuration#nsup-period) in the Aerospike documentation.

Failing to do so will result in the following error when using a `timeout` value other than `0` (never expires):

```
ERROR Failed to set TTL (timeout=X). Aerospike namespace supervisor (nsup) is disabled. Error 22: AEROSPIKE_ERR_FAIL_FORBIDDEN
```