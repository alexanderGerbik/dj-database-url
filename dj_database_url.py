import os
import urllib.parse as urlparse


class ParseError(ValueError):
    def __str__(self):
        return (
            "This string is not a valid url, possibly because some of its parts"
            " is not properly urllib.parse.quote()'ed."
        )


class UnknownSchemeError(ValueError):
    def __init__(self, scheme):
        self.scheme = scheme

    def __str__(self):
        return (
            f"Scheme '{self.scheme}://' is unknown."
            " Did you forget to register custom backend?"
        )


ENGINE_SCHEMES = {}


def default_postprocess(parsed_config):
    pass


class Engine:
    def __init__(self, backend, postprocess=default_postprocess):
        self.backend = backend
        self.postprocess = postprocess


def register(backend, schemes=None):
    engine = Engine(backend)
    schemes = schemes or [backend.rsplit(".")[-1]]
    schemes = [schemes] if isinstance(schemes, str) else schemes
    for scheme in schemes:
        if scheme not in ENGINE_SCHEMES:
            urlparse.uses_netloc.append(scheme)
        ENGINE_SCHEMES[scheme] = engine

    def inner(func):
        engine.postprocess = func
        return func

    return inner


register("django.contrib.gis.db.backends.spatialite")
register("mysql.connector.django", "mysql-connector")
register("django.contrib.gis.db.backends.mysql", "mysqlgis")
register("django.contrib.gis.db.backends.oracle", "oraclegis")
register("django_cockroachdb", "cockroach")


@register("django.db.backends.sqlite3", "sqlite")
def default_to_in_memory_db(parsed_config):
    # mimic sqlalchemy behaviour
    if parsed_config["NAME"] == "":
        parsed_config["NAME"] = ":memory:"


@register("django.db.backends.oracle")
@register("mssql", "mssqlms")
@register("sql_server.pyodbc", "mssql")
def stringify_port(parsed_config):
    parsed_config["PORT"] = str(parsed_config["PORT"])


@register("django.db.backends.mysql", ("mysql", "mysql2"))
def apply_ssl_ca(parsed_config):
    options = parsed_config["OPTIONS"]
    ca = options.pop("ssl-ca", None)
    if ca:
        options["ssl"] = {"ca": ca}


@register("django.db.backends.postgresql", ("postgres", "postgresql", "pgsql"))
@register("django.contrib.gis.db.backends.postgis")
@register("django_redshift_backend", "redshift")
@register("timescale.db.backends.postgresql", "timescale")
@register("timescale.db.backends.postgis", "timescalegis")
def apply_current_schema(parsed_config):
    options = parsed_config["OPTIONS"]
    schema = options.pop("currentSchema", None)
    if schema:
        options["options"] = f"-c search_path={schema}"


def config(env="DATABASE_URL", default=None, **settings):
    """
    Gets a database URL from environmental variable named as 'env' value and parses it.
    """
    s = os.environ.get(env, default)
    return parse(s, **settings) if s else {}


def address_deprecated_arguments(backend, settings):
    import warnings

    if backend is not None:
        message = (
            "Using positional argument `backend`"
            " to override database backend is deprecated."
            " Use keyword argument `ENGINE` instead."
        )
        warnings.warn(message)
        settings["ENGINE"] = backend

    if "engine" in settings:
        message = "The `engine` argument is deprecated. Use `ENGINE` instead."
        warnings.warn(message)
        settings["ENGINE"] = settings.pop("engine")

    if "conn_max_age" in settings:
        warnings.warn(
            "The `conn_max_age` argument is deprecated. Use `CONN_MAX_AGE` instead."
        )
        settings["CONN_MAX_AGE"] = settings.pop("conn_max_age")

    if "ssl_require" in settings:
        warnings.warn(
            "The `ssl_require` argument is deprecated."
            " Use `OPTIONS={'sslmode': 'require'}` instead."
        )
        settings.pop("ssl_require")
        options = settings.pop("OPTIONS", {})
        options["sslmode"] = "require"
        settings["OPTIONS"] = options
    return backend


def parse(url, backend=None, **settings):
    """Parses a database URL and returns configured DATABASE dictionary."""

    address_deprecated_arguments(backend, settings)

    if url == "sqlite://:memory:":
        # this is a special case, because if we pass this URL into
        # urlparse, urlparse will choke trying to interpret "memory"
        # as a port number
        return {"ENGINE": ENGINE_SCHEMES["sqlite"].backend, "NAME": ":memory:"}
        # note: no other settings are required for sqlite

    try:
        url = urlparse.urlsplit(url)
        engine = ENGINE_SCHEMES.get(url.scheme)
        if engine is None:
            raise UnknownSchemeError(url.scheme)
        path = url.path[1:]
        query = urlparse.parse_qs(url.query)
        options = {k: (v[0] if len(v) == 1 else v) for k, v in query.items()}
        parsed_config = {
            "ENGINE": engine.backend,
            "USER": urlparse.unquote(url.username or ""),
            "PASSWORD": urlparse.unquote(url.password or ""),
            "HOST": urlparse.unquote(url.hostname or ""),
            "PORT": url.port or "",
            "NAME": urlparse.unquote(path),
            "OPTIONS": options,
        }
    except UnknownSchemeError:
        raise
    except ValueError:
        raise ParseError() from None

    # Guarantee that config has options, possibly empty, when postprocess() is called
    assert isinstance(parsed_config["OPTIONS"], dict)
    engine.postprocess(parsed_config)

    # Update the final config with any settings passed in explicitly.
    parsed_config["OPTIONS"].update(settings.pop("OPTIONS", {}))
    parsed_config.update(**settings)

    if not parsed_config["OPTIONS"]:
        parsed_config.pop("OPTIONS")
    return parsed_config
