"""
SQL sources put the search term inside a single-quoted literal. A quote in the
term must stay part of that literal, in the way each dialect writes one.
"""

import sqlite3
import time

import pytest
from django.contrib.auth.models import User

from swirl.connectors.bigquery import BigQuery
from swirl.connectors.db_connector import DBConnector
from swirl.connectors.postgresql import PostgreSQL
from swirl.connectors.snowflake import Snowflake
from swirl.connectors.sqlite3 import Sqlite3
from swirl.models import Search, SearchProvider

TEMPLATE = "select {fields} from {table} where {field1} like '%{query_string}%';"
TERM = "zzz' union select detail, detail from other_table --"


@pytest.mark.parametrize('connector', [DBConnector, Sqlite3, PostgreSQL])
def test_a_quote_is_doubled(connector):
    assert connector.escape_term_for_literal(connector, "o'brien") == "o''brien"
    assert connector.escape_term_for_literal(connector, 'back\\slash') == 'back\\slash'


@pytest.mark.parametrize('connector', [BigQuery, Snowflake])
def test_backslash_dialects_escape_the_quote_and_the_backslash(connector):
    assert connector.escape_term_for_literal(connector, "o'brien") == "o\\'brien"
    assert connector.escape_term_for_literal(connector, "x\\' or y") == "x\\\\\\' or y"


def test_plain_terms_are_unchanged():
    assert DBConnector.escape_term_for_literal(DBConnector, 'release notes 2.1') == 'release notes 2.1'


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'source.db'
    connection = sqlite3.connect(path)
    connection.execute('create table notes (title text, body text)')
    connection.execute("insert into notes values ('first', 'a note about o''brien')")
    connection.execute('create table other_table (detail text)')
    connection.execute("insert into other_table values ('row from the other table')")
    connection.commit()
    connection.close()
    return path


def rows_for(term, database):
    owner = User.objects.create_superuser(f'sql_owner_{abs(hash(term))}', 'sql_owner@example.com', 'not-a-real-password')
    provider = SearchProvider.objects.create(
        owner=owner, name='notes', shared=True, active=True, connector='Sqlite3', url=str(database),
        query_template=TEMPLATE, query_mappings='fields=*,table=notes,field1=body')
    search = Search.objects.create(owner=owner, query_string=term, query_string_processed=term,
                                   searchprovider_list=[provider.id])
    connector = Sqlite3(provider.id, search.id, False, '')
    connector.start_time = time.time()
    connector.query_string_to_provider = term
    connector.construct_query()

    connection = sqlite3.connect(database)
    try:
        return connection.execute(connector.query_to_provider).fetchall()
    finally:
        connection.close()


@pytest.mark.django_db
def test_the_term_stays_inside_the_literal(database):
    assert rows_for(TERM, database) == []


@pytest.mark.django_db
def test_a_term_with_an_apostrophe_finds_its_row(database):
    assert rows_for("o'brien", database) == [('first', "a note about o'brien")]
