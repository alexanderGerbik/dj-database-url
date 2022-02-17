import re
from unittest.mock import patch

import pytest

import dj_database_url

URL = "postgres://user:password@localhost/db-name"
EXPECTED_POSTGRES_ENGINE = "django.db.backends.postgresql"

# These were supported out of the box in dj-database-url.
dj_database_url.register("mysql.connector.django", "mysql-connector")
dj_database_url.register("sql_server.pyodbc", "mssql")(dj_database_url.stringify_port)
dj_database_url.register("django_redshift_backend", "redshift")(
    dj_database_url.apply_current_schema
)


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


cases = [
    # postgres and postgres-like
    [
        "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "",
            "PASSWORD": "",
            "HOST": "/var/run/postgresql",
            "PORT": "",
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "postgres://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "",
            "PASSWORD": "",
            "HOST": "/Users/postgres/RuN",
            "PORT": "",
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "postgres://ieRaekei9wilaim7:wegauwhgeuioweg@[2001:db8:1234::1234:5678:90af]:5431/d8r82722r2kuvn",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "ieRaekei9wilaim7",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "2001:db8:1234::1234:5678:90af",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {"options": "-c search_path=otherschema"},
        },
    ],
    [
        "postgres://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "#user",
            "PASSWORD": "#password",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "#database",
        },
    ],
    [
        "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {
                "sslmode": "verify-full",
                "sslrootcert": "rds-combined-ca-bundle.pem",
            },
        },
    ],
    [
        "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?",
        {
            "ENGINE": EXPECTED_POSTGRES_ENGINE,
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn",
        {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema",
        {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {"options": "-c search_path=otherschema"},
        },
    ],
    [
        "redshift://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5439/d8r82722r2kuvn?currentSchema=otherschema",
        {
            "ENGINE": "django_redshift_backend",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5439,
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {"options": "-c search_path=otherschema"},
        },
    ],
    # mysql
    [
        "mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true",
        {
            "ENGINE": "django.db.backends.mysql",
            "USER": "bea6eb025ca0d8",
            "PASSWORD": "69772142",
            "HOST": "us-cdbr-east.cleardb.com",
            "PORT": "",
            "NAME": "heroku_97681db3eff7580",
            "OPTIONS": {"reconnect": "true"},
        },
    ],
    [
        "mysql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn?",
        {
            "ENGINE": "django.db.backends.mysql",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 3306,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "mysql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn?ssl-ca=rds-combined-ca-bundle.pem",
        {
            "ENGINE": "django.db.backends.mysql",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 3306,
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {"ssl": {"ca": "rds-combined-ca-bundle.pem"}},
        },
    ],
    [
        "mysqlgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn",
        {
            "ENGINE": "django.contrib.gis.db.backends.mysql",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    [
        "mysql-connector://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn",
        {
            "ENGINE": "mysql.connector.django",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": 5431,
            "NAME": "d8r82722r2kuvn",
        },
    ],
    # mssql
    [
        "mssql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com/d8r82722r2kuvn?driver=ODBC Driver 13 for SQL Server",
        {
            "ENGINE": "sql_server.pyodbc",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com",
            "PORT": "",
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {"driver": "ODBC Driver 13 for SQL Server"},
        },
    ],
    [
        "mssql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com\\insnsnss:12345/d8r82722r2kuvn?driver=ODBC Driver 13 for SQL Server",
        {
            "ENGINE": "sql_server.pyodbc",
            "USER": "uf07k1i6d8ia0v",
            "PASSWORD": "wegauwhgeuioweg",
            "HOST": "ec2-107-21-253-135.compute-1.amazonaws.com\\insnsnss",
            "PORT": "12345",
            "NAME": "d8r82722r2kuvn",
            "OPTIONS": {"driver": "ODBC Driver 13 for SQL Server"},
        },
    ],
    # sqlite
    [
        "sqlite://",
        {
            "ENGINE": "django.db.backends.sqlite3",
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "NAME": ":memory:",
        },
    ],
    ["sqlite://:memory:", {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}],
    # oracle
    [
        "oracle://scott:tiger@oraclehost:1521/hr",
        {
            "ENGINE": "django.db.backends.oracle",
            "USER": "scott",
            "PASSWORD": "tiger",
            "HOST": "oraclehost",
            "PORT": "1521",
            "NAME": "hr",
        },
    ],
    [
        "oracle://scott:tiger@/tnsname",
        {
            "ENGINE": "django.db.backends.oracle",
            "USER": "scott",
            "PASSWORD": "tiger",
            "HOST": "",
            "PORT": "",
            "NAME": "tnsname",
        },
    ],
    [
        "oracle://scott:tiger@/(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=oraclehost)(PORT=1521)))(CONNECT_DATA=(SID=hr)))",
        {
            "ENGINE": "django.db.backends.oracle",
            "USER": "scott",
            "PASSWORD": "tiger",
            "HOST": "",
            "PORT": "",
            "NAME": "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=oraclehost)(PORT=1521)))(CONNECT_DATA=(SID=hr)))",
        },
    ],
    [
        "oraclegis://scott:tiger@oraclehost:1521/hr",
        {
            "ENGINE": "django.contrib.gis.db.backends.oracle",
            "USER": "scott",
            "PASSWORD": "tiger",
            "HOST": "oraclehost",
            "PORT": 1521,
            "NAME": "hr",
        },
    ],
]


@pytest.mark.parametrize("url,expected", [pytest.param(u, e, id=u) for u, e in cases])
def test_successful_parsing(url, expected):
    assert dj_database_url.parse(url) == expected
