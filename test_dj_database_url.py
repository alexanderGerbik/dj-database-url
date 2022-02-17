import pathlib
import re
from unittest.mock import patch

import pytest
import yaml

import dj_database_url

URL = "postgres://user:password@localhost/db-name"


def load_cases():
    cases_file = pathlib.Path(__file__).parent.joinpath("test_cases.yml")
    cases = yaml.safe_load(cases_file.open())
    return [pytest.param(u, e, id=u) for u, e in cases]


# These were supported out of the box in dj-database-url.
dj_database_url.register("mysql.connector.django", "mysql-connector")
dj_database_url.register("sql_server.pyodbc", "mssql")(dj_database_url.stringify_port)
dj_database_url.register("django_redshift_backend", "redshift")(
    dj_database_url.apply_current_schema
)

dj_database_url.register("django_cockroachdb", "cockroach")
dj_database_url.register("mssql", "mssqlms")(dj_database_url.stringify_port)


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


class TestDeprecatedArguments:
    @patch.dict("os.environ", DATABASE_URL=URL)
    def test_config_conn_max_age_setting(self):
        conn_max_age = 600
        message = (
            "The `conn_max_age` argument is deprecated. Use `CONN_MAX_AGE` instead."
        )
        with pytest.warns(Warning, match=re.escape(message)):
            url = dj_database_url.config(conn_max_age=conn_max_age)

        assert url["CONN_MAX_AGE"] == conn_max_age

    def test_parse_conn_max_age_setting(self):
        conn_max_age = 600
        message = (
            "The `conn_max_age` argument is deprecated. Use `CONN_MAX_AGE` instead."
        )
        with pytest.warns(Warning, match=re.escape(message)):
            url = dj_database_url.parse(URL, conn_max_age=conn_max_age)

        assert url["CONN_MAX_AGE"] == conn_max_age

    @patch.dict("os.environ", DATABASE_URL=URL)
    def test_config_engine_setting(self):
        engine = "django_mysqlpool.backends.mysqlpool"
        message = "The `engine` argument is deprecated. Use `ENGINE` instead."
        with pytest.warns(Warning, match=re.escape(message)):
            url = dj_database_url.config(engine=engine)

        assert url["ENGINE"] == engine

    @patch.dict("os.environ", DATABASE_URL=URL)
    def test_parse_engine_setting(self):
        engine = "django_mysqlpool.backends.mysqlpool"
        message = (
            "Using positional argument `backend`"
            " to override database backend is deprecated."
            " Use keyword argument `ENGINE` instead."
        )
        with pytest.warns(Warning, match=re.escape(message)):
            url = dj_database_url.parse(URL, engine)

        assert url["ENGINE"] == engine


def test_credentials_unquoted__raise_value_error():
    expected_message = (
        "This string is not a valid url, possibly because some of its parts "
        r"is not properly urllib.parse.quote()'ed."
    )
    with pytest.raises(ValueError, match=re.escape(expected_message)):
        dj_database_url.parse("postgres://user:passw#ord!@localhost/foobar")


def test_credentials_quoted__ok():
    config = dj_database_url.parse(
        "postgres://user%40domain:p%23ssword!@localhost/foobar"
    )
    assert config["USER"] == "user@domain"
    assert config["PASSWORD"] == "p#ssword!"


def test_unknown_scheme__raise_value_error():
    expected_message = (
        "Scheme 'unknown-scheme://' is unknown. Did you forget to register custom"
        " backend?"
    )
    with pytest.raises(ValueError, match=expected_message):
        dj_database_url.parse("unknown-scheme://user:password@localhost/foobar")


def test_provide_test_settings__add_them_to_final_config():
    settings = {
        "TEST": {
            "NAME": "mytestdatabase",
        },
    }
    config = dj_database_url.parse(URL, **settings)
    assert config["TEST"] == {"NAME": "mytestdatabase"}


def test_provide_options__add_them_to_final_config():
    options = {"options": "-c search_path=other_schema"}
    config = dj_database_url.parse(URL, OPTIONS=options)
    assert config["OPTIONS"] == options


def test_provide_clashing_options__use_options_from_kwargs():
    options = {"reconnect": "false"}
    config = dj_database_url.parse(f"{URL}?reconnect=true", OPTIONS=options)
    assert config["OPTIONS"]["reconnect"] == "false"


def test_provide_custom_engine__use_it_in_final_config():
    engine = "django_mysqlpool.backends.mysqlpool"
    config = dj_database_url.parse(URL, ENGINE=engine)
    assert config["ENGINE"] == engine


def test_provide_conn_max_age__use_it_in_final_config():
    config = dj_database_url.parse(URL, CONN_MAX_AGE=600)
    assert config["CONN_MAX_AGE"] == 600


@patch.dict("os.environ", DATABASE_URL=URL)
@patch.object(dj_database_url, "parse")
def test_call_config__pass_env_var_value_to_parse(mocked_parse):
    assert dj_database_url.config() == mocked_parse.return_value
    mocked_parse.assert_called_once_with(URL)


@patch.object(dj_database_url, "parse")
def test_call_config_no_var_set__return_empty(mocked_parse):
    assert dj_database_url.config() == {}
    mocked_parse.assert_not_called()


@patch.object(dj_database_url, "parse")
def test_call_config_no_var_set_provide_default__pass_default_to_parse(mocked_parse):
    fallback_url = "sqlite://"
    assert dj_database_url.config(default=fallback_url) == mocked_parse.return_value
    mocked_parse.assert_called_once_with(fallback_url)


@patch.dict("os.environ", CUSTOM_DATABASE_URL=URL)
@patch.object(dj_database_url, "parse")
def test_call_config_custom_env_var__pass_var_value_to_parse(mocked_parse):
    assert dj_database_url.config("CUSTOM_DATABASE_URL") == mocked_parse.return_value
    mocked_parse.assert_called_once_with(URL)


@patch.dict("os.environ", CUSTOM_DATABASE_URL=URL)
@patch.object(dj_database_url, "parse")
def test_provide_settings_to_config__pass_them_to_parse(mocked_parse):
    settings = {
        "CONN_MAX_AGE": 600,
        "ENGINE": "django_mysqlpool.backends.mysqlpool",
        "OPTIONS": {"options": "-c search_path=other_schema"},
    }

    rv = dj_database_url.config("CUSTOM_DATABASE_URL", **settings)

    assert rv == mocked_parse.return_value
    mocked_parse.assert_called_once_with(URL, **settings)


@pytest.mark.parametrize("url,expected", load_cases())
def test_successful_parsing(url, expected):
    assert dj_database_url.parse(url) == expected
