import os
import re
import unittest
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


class DatabaseTestSuite(unittest.TestCase):
    def test_postgres_parsing(self):
        url = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_postgres_unix_socket_parsing(self):
        url = "postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "/var/run/postgresql"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

        url = "postgres://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["HOST"] == "/Users/postgres/RuN"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

    def test_ipv6_parsing(self):
        url = "postgres://ieRaekei9wilaim7:wegauwhgeuioweg@[2001:db8:1234::1234:5678:90af]:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "2001:db8:1234::1234:5678:90af"
        assert url["USER"] == "ieRaekei9wilaim7"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_postgres_search_path_parsing(self):
        url = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema"
        url = dj_database_url.parse(url)
        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431
        assert url["OPTIONS"]["options"] == "-c search_path=otherschema"
        assert "currentSchema" not in url["OPTIONS"]

    def test_postgres_parsing_with_special_characters(self):
        url = "postgres://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["NAME"] == "#database"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "#user"
        assert url["PASSWORD"] == "#password"
        assert url["PORT"] == 5431

    def test_postgis_parsing(self):
        url = "postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.contrib.gis.db.backends.postgis"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_postgis_search_path_parsing(self):
        url = "postgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema"
        url = dj_database_url.parse(url)
        assert url["ENGINE"] == "django.contrib.gis.db.backends.postgis"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431
        assert url["OPTIONS"]["options"] == "-c search_path=otherschema"
        assert "currentSchema" not in url["OPTIONS"]

    def test_mysql_gis_parsing(self):
        url = "mysqlgis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.contrib.gis.db.backends.mysql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_mysql_connector_parsing(self):
        url = "mysql-connector://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "mysql.connector.django"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_cleardb_parsing(self):
        url = "mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.mysql"
        assert url["NAME"] == "heroku_97681db3eff7580"
        assert url["HOST"] == "us-cdbr-east.cleardb.com"
        assert url["USER"] == "bea6eb025ca0d8"
        assert url["PASSWORD"] == "69772142"
        assert url["PORT"] == ""

    def test_empty_sqlite_url(self):
        url = "sqlite://"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.sqlite3"
        assert url["NAME"] == ":memory:"

    def test_memory_sqlite_url(self):
        url = "sqlite://:memory:"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.sqlite3"
        assert url["NAME"] == ":memory:"

    def test_database_url_with_options(self):
        # Test full options
        os.environ[
            "DATABASE_URL"
        ] = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?sslrootcert=rds-combined-ca-bundle.pem&sslmode=verify-full"
        url = dj_database_url.config()

        assert url["ENGINE"] == EXPECTED_POSTGRES_ENGINE
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431
        assert url["OPTIONS"] == {
            "sslrootcert": "rds-combined-ca-bundle.pem",
            "sslmode": "verify-full",
        }

        # Test empty options
        os.environ[
            "DATABASE_URL"
        ] = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?"
        url = dj_database_url.config()
        assert "OPTIONS" not in url

    def test_mysql_database_url_with_sslca_options(self):
        os.environ[
            "DATABASE_URL"
        ] = "mysql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn?ssl-ca=rds-combined-ca-bundle.pem"
        url = dj_database_url.config()

        assert url["ENGINE"] == "django.db.backends.mysql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 3306
        assert url["OPTIONS"] == {"ssl": {"ca": "rds-combined-ca-bundle.pem"}}

        # Test empty options
        os.environ[
            "DATABASE_URL"
        ] = "mysql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:3306/d8r82722r2kuvn?"
        url = dj_database_url.config()
        assert "OPTIONS" not in url

    def test_oracle_parsing(self):
        url = "oracle://scott:tiger@oraclehost:1521/hr"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.oracle"
        assert url["NAME"] == "hr"
        assert url["HOST"] == "oraclehost"
        assert url["USER"] == "scott"
        assert url["PASSWORD"] == "tiger"
        assert url["PORT"] == "1521"

    def test_oracle_gis_parsing(self):
        url = "oraclegis://scott:tiger@oraclehost:1521/hr"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.contrib.gis.db.backends.oracle"
        assert url["NAME"] == "hr"
        assert url["HOST"] == "oraclehost"
        assert url["USER"] == "scott"
        assert url["PASSWORD"] == "tiger"
        assert url["PORT"] == 1521

    def test_oracle_dsn_parsing(self):
        url = (
            "oracle://scott:tiger@/"
            "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)"
            "(HOST=oraclehost)(PORT=1521)))"
            "(CONNECT_DATA=(SID=hr)))"
        )
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.oracle"
        assert url["USER"] == "scott"
        assert url["PASSWORD"] == "tiger"
        assert url["HOST"] == ""
        assert url["PORT"] == ""

        dsn = (
            "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)"
            "(HOST=oraclehost)(PORT=1521)))"
            "(CONNECT_DATA=(SID=hr)))"
        )

        assert url["NAME"] == dsn

    def test_oracle_tns_parsing(self):
        url = "oracle://scott:tiger@/tnsname"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.oracle"
        assert url["USER"] == "scott"
        assert url["PASSWORD"] == "tiger"
        assert url["NAME"] == "tnsname"
        assert url["HOST"] == ""
        assert url["PORT"] == ""

    def test_redshift_parsing(self):
        url = "redshift://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5439/d8r82722r2kuvn?currentSchema=otherschema"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django_redshift_backend"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5439
        assert url["OPTIONS"]["options"] == "-c search_path=otherschema"
        assert "currentSchema" not in url["OPTIONS"]

    def test_mssql_parsing(self):
        url = "mssql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com/d8r82722r2kuvn?driver=ODBC Driver 13 for SQL Server"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "sql_server.pyodbc"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == ""
        assert url["OPTIONS"]["driver"] == "ODBC Driver 13 for SQL Server"
        assert "currentSchema" not in url["OPTIONS"]

    def test_mssql_instance_port_parsing(self):
        url = "mssql://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com\\insnsnss:12345/d8r82722r2kuvn?driver=ODBC Driver 13 for SQL Server"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "sql_server.pyodbc"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com\\insnsnss"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == "12345"
        assert url["OPTIONS"]["driver"] == "ODBC Driver 13 for SQL Server"
        assert "currentSchema" not in url["OPTIONS"]
