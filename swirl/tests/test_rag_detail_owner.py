"""
The RAG detail endpoint returns, and can regenerate, the AI answer stored for
a search. Only the owner of that search may use it.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from swirl.models import Result, Search

URL = '/api/swirl/sapi/detail-search-rag/'
ANSWER = 'stored answer for the owner'


@pytest.fixture
def owner(db):
    return User.objects.create_user('rag_owner', 'rag_owner@example.com', 'not-a-real-password')


@pytest.fixture
def other(db):
    return User.objects.create_user('rag_other', 'rag_other@example.com', 'not-a-real-password')


@pytest.fixture
def search(owner):
    search = Search.objects.create(owner=owner, query_string='q', searchprovider_list=[1],
                                   status='FULL_RESULTS_READY')
    Result.objects.create(owner=owner, search_id=search, searchprovider='ChatGPT', json_results=[{
        'rag_query_items': [], 'body': [ANSWER],
        'additional_content': {'sources': [{'url': 'https://example.com/a'}]},
    }])
    return search


def client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.get_or_create(user=user)[0].key}')
    return client


def test_owner_gets_the_stored_answer(owner, search):
    response = client_for(owner).get(URL, {'search_id': search.pk})

    assert response.status_code == 200
    assert response.json()['message'] == ANSWER


def test_another_user_is_told_the_search_does_not_exist(other, search):
    response = client_for(other).get(URL, {'search_id': search.pk})

    assert response.status_code == 404
    assert ANSWER not in response.content.decode()


def test_another_user_cannot_regenerate_the_answer(other, search):
    response = client_for(other).get(URL, {'search_id': search.pk, 'ai_instructions': 'x'})

    assert response.status_code == 404
    assert Result.objects.filter(search_id=search, searchprovider='ChatGPT').count() == 1


def test_unknown_search_gets_the_same_answer_as_another_users(other, search):
    theirs = client_for(other).get(URL, {'search_id': search.pk})
    unknown = client_for(other).get(URL, {'search_id': search.pk + 1000})

    assert unknown.status_code == theirs.status_code == 404
    assert unknown.content == theirs.content


def test_a_search_id_that_is_not_a_number_is_not_found(other, search):
    assert client_for(other).get(URL, {'search_id': 'abc'}).status_code == 404
