import os
import urllib.parse as urlparse

ENGINE_SCHEMES = {}


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


def default_postprocess(config):
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
        urlparse.uses_netloc.append(scheme)
        ENGINE_SCHEMES[scheme] = engine

    def inner(func):
        engine.postprocess = func
        return func

    return inner


register("django.contrib.gis.db.backends.spatialite")
register("django.contrib.gis.db.backends.mysql", "mysqlgis")
register("django.contrib.gis.db.backends.oracle", "oraclegis")


@register("django.db.backends.sqlite3", "sqlite")
def default_to_in_memory_db(config):
    # mimic sqlalchemy behaviour
    if config["NAME"] == "":
        config["NAME"] = ":memory:"


@register("django.db.backends.oracle")
def stringify_port(config):
    config["PORT"] = str(config["PORT"])


@register("django.db.backends.mysql")
def apply_ssl_ca(config):
    options = config["OPTIONS"]
    ca = options.pop("ssl-ca", None)
    if ca:
        options["ssl"] = {"ca": ca}


@register("django.db.backends.postgresql", ("postgres", "postgresql", "pgsql"))
@register("django.contrib.gis.db.backends.postgis")
def apply_current_schema(config):
    options = config["OPTIONS"]
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
        if settings.pop("ssl_require"):
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
        url = urlparse.urlparse(url)
        engine = ENGINE_SCHEMES.get(url.scheme)
        if engine is None:
            raise UnknownSchemeError(url.scheme)
        path = url.path[1:]
        query = urlparse.parse_qs(url.query)
        options = {k: (v[0] if len(v) == 1 else v) for k, v in query.items()}
        config = {
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
    assert isinstance(config["OPTIONS"], dict)
    engine.postprocess(config)

    # Update the final config with any settings passed in explicitly.
    config["OPTIONS"].update(settings.pop("OPTIONS", {}))
    config.update(**settings)

    if not config["OPTIONS"]:
        config.pop("OPTIONS")
    return config
