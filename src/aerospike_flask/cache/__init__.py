"""
    aerospike_flask.cache
    ~~~~~~~~~~~~~~~~~~~~~

    Aerospike module implementing custom cache backend for Flask-Caching.

    :copyright: (c) 2024 by Micah Carrick.
    :license: BSD, see LICENSE for more details.
"""

__version__ = "0.1.1.rc3"


def get_version():
    """Get the module version string.

    :return: The module version as a semantic version string
    :rtype: str
    """
    return __version__
