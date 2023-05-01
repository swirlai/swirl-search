import json
from django.test import TestCase
import swirl_server.settings as settings
import pytest
import logging
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from swirl.processors.adaptive import *
from swirl.processors.transform_query_processor import *
from swirl.processors.utils import str_tok_get_prefixes, date_str_to_timestamp, highlight_list
from swirl.processors.result_map_url_encoder import ResultMapUrlEncoder

logger = logging.getLogger(__name__)

######################################################################
## fixtures

## General and shared

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_suser_pw():
    return 'password'

@pytest.fixture
def test_suser(test_suser_pw):
    return User.objects.create_user(
        username='admin',
        password=test_suser_pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

## Test data
@pytest.fixture
def qrx_record_1():
    return {
        "name": "xxx",
        "shared": True,
        "qrx_type": "rewrite",
        "config_content": "# This is a test\n# column1, colum2\nmobiles; ombile; mo bile, mobile\ncheapest smartphones, cheap smartphone"
}

@pytest.fixture
def qrx_synonym():
    return {
        "name": "synonym 1",
        "shared": True,
        "qrx_type": "synonym",
        "config_content": "# column1, column2\nnotebook, laptop\nlaptop, personal computer\npc, personal computer\npersonal computer, pc"
}

@pytest.fixture
def qrx_synonym_bag():
    return {
        "name": "bag 1",
        "shared": True,
        "qrx_type": "bag",
        "config_content": "# column1....columnN\nnotebook, personal computer, laptop, pc\ncar,automobile, ride"
}

@pytest.fixture
def noop_query_string():
    return "noop"


######################################################################
## tests
######################################################################

@pytest.fixture
def hll_test_cases():
    return [
            ['Swirl_Pitch_1234412',['swirl']],
            ['Swirl Pitch 1234412',['swirl']],
            ['I love programming in Python',['programming', 'Python']],
            ['The quick brown fox jumps over the lazy dog',['quick', 'jumps', 'dog']],
            ['The weather is nice today',['rain', 'snow', 'sun']],
            ['ChatGPT is an AI language model', ['ChatGPT', 'AI', 'language', 'model']],
            ['This is a case insensitive test',["this", "Test"]]
        ]

@pytest.fixture
def hll_test_expected():
    return[
        '<em>Swirl</em>_Pitch_1234412',
        '<em>Swirl</em> Pitch 1234412',
        'I love <em>programming</em> in <em>Python</em>',
        'The <em>quick</em> brown fox <em>jumps</em> over the lazy <em>dog</em>',
        'The weather is nice today',
        '<em>ChatGPT</em> is an <em>AI</em> <em>language</em> <em>model</em>',
        '<em>This</em> is a case insensitive <em>test</em>'
    ]

def test_highlght_list(hll_test_cases, hll_test_expected):
    i = 0
    for c in hll_test_cases:
        x = highlight_list(c[0],c[1])
        assert x == hll_test_expected[i]
        i = i + 1

@pytest.fixture
def aqp_test_cases():
    return ['NOT foo',
            'elon NOT twitter',
            'news:elon NOT twitter']

@pytest.fixture
def aqp_test_expected():
    return['-foo',
           'elon -twitter',
           'elon -twitter'
        ]

@pytest.mark.django_db
def test_aqp(aqp_test_cases, aqp_test_expected):
    i = 0
    for tc in aqp_test_cases:
        aqp = AdaptiveQueryProcessor(tc,
            'cx=0c38029ddd002c006,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-',
            ['News', 'EnterpriseSearch']
        )
        actual = aqp.process()
        assert actual == aqp_test_expected[i]
        i = i + 1

@pytest.fixture
def rm_url_encoder_test_cases():
    return {
        'foo':'bar',
        'sw_urlencode(bar)':'baz',
        'sw_urlencode(yyz)':'foo==',
        'sw_urlencode(yyz':'foo==',
        'foo(yyz)':'foo==',
        'sw_urlencode(hitId)':'askjfasdkj,,l::":kajsdf==alksfja;lkdjs==='
    }

@pytest.fixture
def rm_url_encoder_test_expected():
    return {
        'foo':{'key':'foo', 'value':'bar'},
        'sw_urlencode(bar)':{'key':'bar', 'value':'baz'},
        'sw_urlencode(yyz)':{'key':'yyz', 'value':'foo%3D%3D'},
        'sw_urlencode(yyz': {'key':'sw_urlencode(yyz', 'value':'foo=='},
        'foo(yyz)': {'key':'foo(yyz)', 'value':'foo=='},
        'sw_urlencode(hitId)': {'key':'hitId', 'value':'askjfasdkj%2C%2Cl%3A%3A%22%3Akajsdf%3D%3Dalksfja%3Blkdjs%3D%3D%3D'}
    }

@pytest.mark.django_db
def test_rm_url_encoder(rm_url_encoder_test_cases, rm_url_encoder_test_expected):
    for k in rm_url_encoder_test_cases.keys():
        uc  = ResultMapUrlEncoder(k)
        assert uc.get_key() == rm_url_encoder_test_expected[k].get('key')
        assert uc.get_value(rm_url_encoder_test_cases.get(k)) == rm_url_encoder_test_expected[k].get('value')

    # Boundary cases:
    uc  = ResultMapUrlEncoder(None)
    k = uc.get_key()
    v = uc.get_value('foo')
    assert k == None
    assert v == 'foo'

    uc  = ResultMapUrlEncoder('')
    k = uc.get_key()
    v = uc.get_value('foo')
    assert k == ''
    assert v == 'foo'





@pytest.fixture
def prefix_toks_test_cases():
    return [
        ['one'],
        ['one','two'],
        ['one','two', 'three']
    ]

@pytest.fixture
def prefix_toks_test_expected():
    return [
        ['one'],
        ['one two','one','two'],
        ['one two three','one two','one','two three','two','three'],
    ]

@pytest.mark.django_db
def test_utils_prefix_toks(prefix_toks_test_cases, prefix_toks_test_expected):
    assert prefix_toks_test_cases[0] == ['one']
    i = 0
    for c in prefix_toks_test_cases:
        ret = str_tok_get_prefixes(c)
        assert ret == prefix_toks_test_expected[i]
        i = i + 1


@pytest.fixture
def utils_date_str_to_timestamp_cases():
    return ['1681393728.832229','1681393728','Jan 17, 1975']

@pytest.fixture
def utils_date_str_to_timestamp_expected():
    return['2023-04-13 09:48:48.832229','2023-04-13 09:48:48','1975-01-17 00:00:00']

@pytest.mark.django_db
def test_utils_date_str_to_timestamp(utils_date_str_to_timestamp_cases, utils_date_str_to_timestamp_expected):
    i = 0
    for c in utils_date_str_to_timestamp_cases:
        ret = date_str_to_timestamp(c)
        assert ret == utils_date_str_to_timestamp_expected[i]
        i = i + 1


@pytest.mark.django_db
def test_query_transform_viewset_crud(api_client, test_suser, test_suser_pw, qrx_record_1):

    is_logged_in = api_client.login(username=test_suser.username, password=test_suser_pw)

    # Check if the login was successful
    assert is_logged_in, 'Client login failed'
    response = api_client.post(reverse('create'),data=qrx_record_1, format='json')

    assert response.status_code == 201, 'Expected HTTP status code 201'
    # Call the viewset
    response = api_client.get(reverse('querytransforms/list'))

    # Check if the response is successful
    assert response.status_code == 200, 'Expected HTTP status code 200'

    # Check if the number of users in the response is correct
    assert len(response.json()) == 1, 'Expected 1 transform'

    # Check if the data is correct
    content = response.json()[0]
    assert content.get('name','') == qrx_record_1.get('name')
    assert content.get('shared','') == qrx_record_1.get('shared')
    assert content.get('qrx_type','') == qrx_record_1.get('qrx_type')
    assert content.get('config_content','') == qrx_record_1.get('config_content')

    # test retrieve
    purl = reverse('retrieve', kwargs={'pk': 1})
    response = api_client.get(purl,  format='json')
    assert response.status_code == 200, 'Expected HTTP status code 201'
    assert len(response.json()) == 8, 'Expected 1 transform'
    content = response.json()
    assert content.get('name','') == qrx_record_1.get('name')
    assert content.get('shared','') == qrx_record_1.get('shared')
    assert content.get('qrx_type','') == qrx_record_1.get('qrx_type')
    assert content.get('config_content','') == qrx_record_1.get('config_content')

    # test update
    qrx_record_1['config_content'] = "# This is an update\n# column1, colum2\nmobiles; ombile; mo bile, mobile\ncheapest smartphones, cheap smartphone"
    purl = reverse('update', kwargs={'pk': 1})
    response = api_client.put(purl, data=qrx_record_1, format='json')
    assert response.status_code == 201, 'Expected HTTP status code 201'
    response = api_client.get(reverse('querytransforms/list'))
    assert response.status_code == 200, 'Expected HTTP status code 200'
    assert len(response.json()) == 1, 'Expected 1 transform'
    content = response.json()[0]
    assert content.get('config_content','') == qrx_record_1.get('config_content')

    # test delete
    purl = reverse('delete', kwargs={'pk': 1})
    response = api_client.delete(purl)
    assert response.status_code == 410, 'Expected HTTP status code 410'

@pytest.mark.django_db
def test_query_trasnform_unique(api_client, test_suser, test_suser_pw, qrx_record_1):

    is_logged_in = api_client.login(username=test_suser.username, password=test_suser_pw)

    # Check if the login was successful
    assert is_logged_in, 'Client login failed'
    response = api_client.post(reverse('create'),data=qrx_record_1, format='json')

    assert response.status_code == 201, 'Expected HTTP status code 201'
    # Call the viewset
    response = api_client.get(reverse('querytransforms/list'))

    # Check if the response is successful
    assert response.status_code == 200, 'Expected HTTP status code 200'

    # Check if the number of users in the response is correct
    assert len(response.json()) == 1, 'Expected 1 transform'

    # Check if the data is correct
    content = response.json()[0]
    assert content.get('name','') == qrx_record_1.get('name')
    assert content.get('shared','') == qrx_record_1.get('shared')
    assert content.get('qrx_type','') == qrx_record_1.get('qrx_type')
    assert content.get('config_content','') == qrx_record_1.get('config_content')

    ## try to create it again
    response = api_client.post(reverse('create'),data=qrx_record_1, format='json')
    assert response.status_code == 400, 'Expected HTTP status code 400'
