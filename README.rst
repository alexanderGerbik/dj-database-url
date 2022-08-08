DJ-Database-URL
~~~~~~~~~~~~~~~

.. image:: https://jazzband.co/static/img/badge.png
   :target: https://jazzband.co/
   :alt: Jazzband

.. image:: https://github.com/jazzband/dj-database-url/actions/workflows/test.yml/badge.svg
   :target: https://github.com/jazzband/dj-database-url/actions/workflows/test.yml

.. image:: https://codecov.io/gh/jazzband/dj-database-url/branch/master/graph/badge.svg?token=7srBUpszOa
   :target: https://codecov.io/gh/jazzband/dj-database-url

This simple Django utility allows you to utilize the
`12factor <http://www.12factor.net/backing-services>`_ inspired
``DATABASE_URL`` environment variable to configure your Django application.

Installation
------------

Installation is simple::

    $ pip install dj-database-url

Usage
-----

The ``dj_database_url.config()`` method returns a Django database
connection dictionary, populated with all the data specified in your
``DATABASE_URL`` environment variable::

    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(),
        # arbitrary environment variable can be used
        "replica": dj_database_url.config("REPLICA_URL"),
    }

Given the following environment variables are defined::

    $ export DATABASE_URL="postgres://user:password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/db-name"
    # All the characters which are reserved in URL as per RFC 3986 should be urllib.parse.quote()'ed.
    $ export REPLICA_URL="postgres://%23user:%23password@replica-host.com/db-name?timeout=20"

The above-mentioned code will result in::

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "USER": "user",
            "PASSWORD": "password",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "db-name",
        },
        "replica": {
            "ENGINE": "django.db.backends.postgresql",
            "USER": "#user",
            "PASSWORD": "#password",
            "HOST": "replica-host.com",
            "PORT": "",
            "NAME": "db-name",
            # Any querystring parameters are automatically parsed and added to `OPTIONS`.
            "OPTIONS": {
                "timeout": "20",
            },
        },
    }

A default value can be provided which will be used when the environment
variable is not set::

    DATABASES["default"] = dj_database_url.config(default="sqlite://")

If you'd rather not use an environment variable, you can pass a URL
directly into ``dj_database_url.parse()``::

    DATABASES["default"] = dj_database_url.parse("postgres://...")

You can also pass in any keyword argument that Django's |databases hyperlink|_ setting accepts,
such as |max age hyperlink|_ or |options hyperlink|_::

    dj_database_url.config(CONN_MAX_AGE=600, TEST={"NAME": "mytestdatabase"})
    # results in:
    {
        "ENGINE": "django.db.backends.postgresql",
        # ... other values coming from DATABASE_URL
        "CONN_MAX_AGE": 600,
        "TEST": {
            "NAME": "mytestdatabase",
        },
    }

    # such usage is also possible:
    dj_database_url.parse("postgres://...", **{
        "CONN_MAX_AGE": 600,
        "TEST": {
            "NAME": "mytestdatabase",
        },
        "OPTIONS": {
            "isolation_level": psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
        },
    })

``OPTIONS`` will be properly merged with the parameters coming from
querystring (keyword argument has higher priority than querystring).

.. |databases hyperlink| replace:: ``DATABASES``
.. _databases hyperlink: https://docs.djangoproject.com/en/stable/ref/settings/#databases
.. |max age hyperlink| replace:: ``CONN_MAX_AGE``
.. _max age hyperlink: https://docs.djangoproject.com/en/stable/ref/settings/#conn-max-age
.. |options hyperlink| replace:: ``OPTIONS``
.. _options hyperlink: https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-OPTIONS

Supported Databases
-------------------

Support currently exists for PostgreSQL, PostGIS, MySQL, MySQL (GIS),
Oracle, Oracle (GIS), Redshift, CockroachDB, Timescale, Timescale (GIS) and SQLite.

If you want to use
some non-default backends, you need to register them first::

    import dj_database_url

    # registration should be performed only once
    dj_database_url.register("mysql.connector.django", "mysql-connector")

    assert dj_database_url.parse("mysql-connector://user:password@host:port/db-name") == {
        "ENGINE": "mysql.connector.django",
        # ...other connection params
    }

Some backends need further config adjustments (e.g. oracle and mssql
expect ``PORT`` to be a string). For such cases you can provide a
post-processing function to ``register()`` (note that ``register()`` is
used as a **decorator(!)** in this case)::

    import dj_database_url

    @dj_database_url.register("sql_server.pyodbc", "mssql")
    def stringify_port(config):
        config["PORT"] = str(config["PORT"])

    @dj_database_url.register("django_redshift_backend", "redshift")
    def apply_current_schema(config):
        options = config["OPTIONS"]
        schema = options.pop("currentSchema", None)
        if schema:
            options["options"] = f"-c search_path={schema}"

    @dj_database_url.register("django_snowflake", "snowflake")
    def adjust_snowflake_config(config):
        config.pop("PORT", None)
        config["ACCOUNT"] = config.pop("HOST")
        name, _, schema = config["NAME"].partition("/")
        if schema:
            config["SCHEMA"] = schema
            config["NAME"] = name
        options = config.get("OPTIONS", {})
        warehouse = options.pop("warehouse", None)
        if warehouse:
            config["WAREHOUSE"] = warehouse
        role = options.pop("role", None)
        if role:
            config["ROLE"] = role

URL schema
----------

+----------------------+-----------------------------------------------+--------------------------------------------------+
| Engine               | Django Backend                                | URL                                              |
+======================+===============================================+==================================================+
| PostgreSQL           | ``django.db.backends.postgresql`` [1]_        | ``postgres://USER:PASSWORD@HOST:PORT/NAME`` [2]_ |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| PostGIS              | ``django.contrib.gis.db.backends.postgis``    | ``postgis://USER:PASSWORD@HOST:PORT/NAME``       |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| MSSQL                | ``sql_server.pyodbc``                         | ``mssql://USER:PASSWORD@HOST:PORT/NAME``         |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| MSSQL [5]_           | ``mssql``                                     | ``mssqlms://USER:PASSWORD@HOST:PORT/NAME``       |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| MySQL                | ``django.db.backends.mysql``                  | ``mysql://USER:PASSWORD@HOST:PORT/NAME``         |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| MySQL (GIS)          | ``django.contrib.gis.db.backends.mysql``      | ``mysqlgis://USER:PASSWORD@HOST:PORT/NAME``      |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| SQLite               | ``django.db.backends.sqlite3``                | ``sqlite:///PATH`` [3]_                          |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| SpatiaLite           | ``django.contrib.gis.db.backends.spatialite`` | ``spatialite:///PATH`` [3]_                      |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| Oracle               | ``django.db.backends.oracle``                 | ``oracle://USER:PASSWORD@HOST:PORT/NAME`` [4]_   |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| Oracle (GIS)         | ``django.contrib.gis.db.backends.oracle``     | ``oraclegis://USER:PASSWORD@HOST:PORT/NAME``     |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| Redshift             | ``django_redshift_backend``                   | ``redshift://USER:PASSWORD@HOST:PORT/NAME``      |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| CockroachDB          | ``django_cockroachdb``                        | ``cockroach://USER:PASSWORD@HOST:PORT/NAME``     |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| Timescale [6]_       | ``timescale.db.backends.postgresql``          | ``timescale://USER:PASSWORD@HOST:PORT/NAME``     |
+----------------------+-----------------------------------------------+--------------------------------------------------+
| Timescale (GIS) [6]_ | ``timescale.db.backend.postgis``              | ``timescalegis://USER:PASSWORD@HOST:PORT/NAME``  |
+----------------------+-----------------------------------------------+--------------------------------------------------+

.. [1] The django.db.backends.postgresql backend is named django.db.backends.postgresql_psycopg2 in older releases. For
       backwards compatibility, the old name still works in newer versions. (The new name does not work in older versions).
.. [2] With PostgreSQL, you can also use unix domain socket paths with
       `percent encoding <http://www.postgresql.org/docs/9.2/interactive/libpq-connect.html#AEN38162>`_:
       ``postgres://%2Fvar%2Flib%2Fpostgresql/dbname``.
.. [3] SQLite connects to file based databases. The same URL format is used, omitting
       the hostname, and using the "file" portion as the filename of the database.
       This has the effect of four slashes being present for an absolute file path:
       ``sqlite:////full/path/to/your/database/file.sqlite``.
.. [4] Note that when connecting to Oracle the URL isn't in the form you may know
       from using other Oracle tools (like SQLPlus) i.e. user and password are separated
       by ``:`` not by ``/``. Also you can omit ``HOST`` and ``PORT``
       and provide a full DSN string or TNS name in ``NAME`` part.
.. [5] Microsoft official `mssql-django <https://github.com/microsoft/mssql-django>`_ adapter.
.. [6] Using the django-timescaledb Package which must be installed.


Contributing
------------

We welcome contributions to this project. Projects can take two forms:

1. Raising issues or helping others through the github issue tracker.
2. Contributing code.

Raising Issues or helping others:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When submitting an issue or helping other remember you are talking to humans who have feelings, jobs and lives of their
own. Be nice, be kind, be polite. Remember english may not be someone first language, if you do not understand or
something is not clear be polite and re-ask/ re-word.

Contributing code:
^^^^^^^^^^^^^^^^^^

* Before writing code be sure to check existing PR's and issues in the tracker.
* Write code to the pylint spec.
* Large or wide sweeping changes will take longer, and may face more scrutiny than smaller confined changes.
* Code should be pass `black` and `flake8` validation.
