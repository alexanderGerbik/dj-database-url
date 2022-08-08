import os
import re
import unittest
from urllib.parse import uses_netloc

import dj_database_url

URL = "postgres://user:password@localhost/db-name"


class DeprecatedArgumentsTestSuite(unittest.TestCase):
    def test_config_conn_max_age_setting(self):
        conn_max_age = 600
        os.environ[
            "DATABASE_URL"
        ] = "mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true"
        message = (
            "The `conn_max_age` argument is deprecated. Use `CONN_MAX_AGE` instead."
        )
        with self.assertWarns(Warning, msg=message):
            url = dj_database_url.config(conn_max_age=conn_max_age)

        assert url["CONN_MAX_AGE"] == conn_max_age
        del os.environ["DATABASE_URL"]

    def test_parse_conn_max_age_setting(self):
        conn_max_age = 600
        url = "mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true"
        message = (
            "The `conn_max_age` argument is deprecated. Use `CONN_MAX_AGE` instead."
        )
        with self.assertWarns(Warning, msg=message):
            url = dj_database_url.parse(url, conn_max_age=conn_max_age)

        assert url["CONN_MAX_AGE"] == conn_max_age

    def test_config_engine_setting(self):
        engine = "django_mysqlpool.backends.mysqlpool"
        os.environ[
            "DATABASE_URL"
        ] = "mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true"
        message = "The `engine` argument is deprecated. Use `ENGINE` instead."
        with self.assertWarns(Warning, msg=message):
            url = dj_database_url.config(engine=engine)

        assert url["ENGINE"] == engine
        del os.environ["DATABASE_URL"]

    def test_parse_engine_setting(self):
        engine = "django_mysqlpool.backends.mysqlpool"
        url = "mysql://bea6eb025ca0d8:69772142@us-cdbr-east.cleardb.com/heroku_97681db3eff7580?reconnect=true"
        message = (
            "Using positional argument `backend`"
            " to override database backend is deprecated."
            " Use keyword argument `ENGINE` instead."
        )
        with self.assertWarns(Warning, msg=message):
            url = dj_database_url.parse(url, engine)

        assert url["ENGINE"] == engine

    def test_pass_ssl_require__handle_and_issue_warning(self):
        message = (
            "The `ssl_require` argument is deprecated."
            " Use `OPTIONS={'sslmode': 'require'}` instead."
        )
        with self.assertWarnsRegex(Warning, re.escape(message)):
            config = dj_database_url.parse(URL, ssl_require=True)

        assert config["OPTIONS"] == {'sslmode': 'require'}


class DatabaseTestSuite(unittest.TestCase):
    def test_credentials_unquoted__raise_value_error(self):
        expected_message = (
            "This string is not a valid url, possibly because some of its parts "
            r"is not properly urllib.parse.quote()'ed."
        )
        with self.assertRaisesRegex(ValueError, re.escape(expected_message)):
            dj_database_url.parse("postgres://user:passw#ord!@localhost/foobar")

    def test_credentials_quoted__ok(self):
        url = "postgres://user%40domain:p%23ssword!@localhost/foobar"
        config = dj_database_url.parse(url)
        assert config["USER"] == "user@domain"
        assert config["PASSWORD"] == "p#ssword!"

    def test_unknown_scheme__raise_value_error(self):
        expected_message = "Scheme 'unknown-scheme://' is unknown. Did you forget to register custom backend?"
        with self.assertRaisesRegex(ValueError, re.escape(expected_message)):
            dj_database_url.parse("unknown-scheme://user:password@localhost/foobar")

    def test_provide_test_settings__add_them_to_final_config(self):
        settings = {
            "TEST": {
                "NAME": "mytestdatabase",
            },
        }
        config = dj_database_url.parse(URL, **settings)
        assert config["TEST"] == {"NAME": "mytestdatabase"}

    def test_provide_options__add_them_to_final_config(self):
        options = {"options": "-c search_path=other_schema"}
        config = dj_database_url.parse(URL, OPTIONS=options)
        assert config["OPTIONS"] == options

    def test_provide_clashing_options__use_options_from_kwargs(self):
        options = {"reconnect": "false"}
        config = dj_database_url.parse(f"{URL}?reconnect=true", OPTIONS=options)
        assert config["OPTIONS"]["reconnect"] == "false"

    def test_provide_custom_engine__use_it_in_final_config(self):
        engine = "django_mysqlpool.backends.mysqlpool"
        config = dj_database_url.parse(URL, ENGINE=engine)
        assert config["ENGINE"] == engine

    def test_provide_conn_max_age__use_it_in_final_config(self):
        config = dj_database_url.parse(URL, CONN_MAX_AGE=600)
        assert config["CONN_MAX_AGE"] == 600

    def test_register_multiple_times__no_duplicates_in_uses_netloc(self):
        # make sure that when register() function is misused,
        # it won't pollute urllib.parse.uses_netloc list with duplicates.
        # Otherwise, it might cause performance issue if some code assumes that
        # that list is short and performs linear search on it.
        dj_database_url.register("django.contrib.db.backends.bag_end", "bag-end")
        dj_database_url.register("django.contrib.db.backends.bag_end", "bag-end")
        assert len(uses_netloc) == len(set(uses_netloc))

    def test_postgres_parsing(self):
        url = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_postgres_unix_socket_parsing(self):
        url = "postgres://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "/var/run/postgresql"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

        url = "postgres://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.postgresql"
        assert url["HOST"] == "/Users/postgres/RuN"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

    def test_ipv6_parsing(self):
        url = "postgres://ieRaekei9wilaim7:wegauwhgeuioweg@[2001:db8:1234::1234:5678:90af]:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "django.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "2001:db8:1234::1234:5678:90af"
        assert url["USER"] == "ieRaekei9wilaim7"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_postgres_search_path_parsing(self):
        url = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema"
        url = dj_database_url.parse(url)
        assert url["ENGINE"] == "django.db.backends.postgresql"
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

        assert url["ENGINE"] == "django.db.backends.postgresql"
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

    def test_database_url(self):
        a = dj_database_url.config()
        assert not a

        os.environ[
            "DATABASE_URL"
        ] = "postgres://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"

        url = dj_database_url.config()

        assert url["ENGINE"] == "django.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_sqlite_url(self):
        url = "sqlite:///db.sqlite3"
        config = dj_database_url.parse(url)

        assert config["ENGINE"] == "django.db.backends.sqlite3"
        assert config["NAME"] == "db.sqlite3"

    def test_sqlite_absolute_url(self):
        # 4 slashes are needed:
        # two are part of scheme
        # one separates host:port from path
        # and the fourth goes to "NAME" value
        url = "sqlite:////db.sqlite3"
        config = dj_database_url.parse(url)

        assert config["ENGINE"] == "django.db.backends.sqlite3"
        assert config["NAME"] == "/db.sqlite3"

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

        assert url["ENGINE"] == "django.db.backends.postgresql"
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

    def test_cockroach(self):
        url = "cockroach://testuser:testpass@testhost:26257/cockroach?sslmode=verify-full&sslrootcert=/certs/ca.crt&sslcert=/certs/client.myprojectuser.crt&sslkey=/certs/client.myprojectuser.key"
        url = dj_database_url.parse(url)
        assert url['ENGINE'] == 'django_cockroachdb'
        assert url['NAME'] == 'cockroach'
        assert url['HOST'] == 'testhost'
        assert url['USER'] == 'testuser'
        assert url['PASSWORD'] == 'testpass'
        assert url['PORT'] == 26257
        assert url['OPTIONS']['sslmode'] == 'verify-full'
        assert url['OPTIONS']['sslrootcert'] == '/certs/ca.crt'
        assert url['OPTIONS']['sslcert'] == '/certs/client.myprojectuser.crt'
        assert url['OPTIONS']['sslkey'] == '/certs/client.myprojectuser.key'

    def test_mssqlms_parsing(self):
        url = "mssqlms://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com/d8r82722r2kuvn?driver=ODBC Driver 13 for SQL Server"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "mssql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == ""
        assert url["OPTIONS"]["driver"] == "ODBC Driver 13 for SQL Server"
        assert "currentSchema" not in url["OPTIONS"]

    def test_timescale_parsing(self):
        url = "timescale://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_timescale_unix_socket_parsing(self):
        url = "timescale://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "/var/run/postgresql"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

        url = "timescale://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgresql"
        assert url["HOST"] == "/Users/postgres/RuN"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

    def test_timescale_ipv6_parsing(self):
        url = "timescale://ieRaekei9wilaim7:wegauwhgeuioweg@[2001:db8:1234::1234:5678:90af]:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "2001:db8:1234::1234:5678:90af"
        assert url["USER"] == "ieRaekei9wilaim7"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_timescale_search_path_parsing(self):
        url = "timescale://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema"
        url = dj_database_url.parse(url)
        assert url["ENGINE"] == "timescale.db.backends.postgresql"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431
        assert url["OPTIONS"]["options"] == "-c search_path=otherschema"
        assert "currentSchema" not in url["OPTIONS"]

    def test_timescale_parsing_with_special_characters(self):
        url = "timescale://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgresql"
        assert url["NAME"] == "#database"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "#user"
        assert url["PASSWORD"] == "#password"
        assert url["PORT"] == 5431

    def test_timescalegis_parsing(self):
        url = "timescalegis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgis"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_timescalegis_unix_socket_parsing(self):
        url = "timescalegis://%2Fvar%2Frun%2Fpostgresql/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgis"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "/var/run/postgresql"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

        url = "timescalegis://%2FUsers%2Fpostgres%2FRuN/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgis"
        assert url["HOST"] == "/Users/postgres/RuN"
        assert url["USER"] == ""
        assert url["PASSWORD"] == ""
        assert url["PORT"] == ""

    def test_timescalegis_ipv6_parsing(self):
        url = "timescalegis://ieRaekei9wilaim7:wegauwhgeuioweg@[2001:db8:1234::1234:5678:90af]:5431/d8r82722r2kuvn"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgis"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "2001:db8:1234::1234:5678:90af"
        assert url["USER"] == "ieRaekei9wilaim7"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431

    def test_timescalegis_search_path_parsing(self):
        url = "timescalegis://uf07k1i6d8ia0v:wegauwhgeuioweg@ec2-107-21-253-135.compute-1.amazonaws.com:5431/d8r82722r2kuvn?currentSchema=otherschema"
        url = dj_database_url.parse(url)
        assert url["ENGINE"] == "timescale.db.backends.postgis"
        assert url["NAME"] == "d8r82722r2kuvn"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "uf07k1i6d8ia0v"
        assert url["PASSWORD"] == "wegauwhgeuioweg"
        assert url["PORT"] == 5431
        assert url["OPTIONS"]["options"] == "-c search_path=otherschema"
        assert "currentSchema" not in url["OPTIONS"]

    def test_timescalegis_parsing_with_special_characters(self):
        url = "timescalegis://%23user:%23password@ec2-107-21-253-135.compute-1.amazonaws.com:5431/%23database"
        url = dj_database_url.parse(url)

        assert url["ENGINE"] == "timescale.db.backends.postgis"
        assert url["NAME"] == "#database"
        assert url["HOST"] == "ec2-107-21-253-135.compute-1.amazonaws.com"
        assert url["USER"] == "#user"
        assert url["PASSWORD"] == "#password"
        assert url["PORT"] == 5431


if __name__ == "__main__":
    unittest.main()
