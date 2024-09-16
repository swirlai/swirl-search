import time
import json
import os
from django.test import TestCase
from swirl.models import SearchProvider
from swirl.serializers import SearchProviderSerializer
import swirl_server.settings as settings
import pytest
from unittest import mock
import logging
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from swirl.processors.adaptive import *
from swirl.processors.gen_ai_query import *
from swirl.processors.transform_query_processor import *
from swirl.processors.utils import str_tok_get_prefixes, date_str_to_timestamp, highlight_list, match_all, tokenize_word_list
from swirl.processors.result_map_converter import ResultMapConverter
from swirl.processors.dedupe import DedupeByFieldResultProcessor
from swirl.processors.relevancy import DropIrrelevantPostResultProcessor
from swirl.utils import select_providers, http_auth_parse


logger = logging.getLogger(__name__)

TEST_AI_MODEL = "fake-model"

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

def test_http_auth_parse():
    a = http_auth_parse("HTTPBasicAuth('leto@arakis.planet','gomjabar')")
    assert len(a) == 2
    assert a[0] == 'HTTPBasicAuth'
    assert len(a[1]) == 2
    assert a[1][0] == "leto@arakis.planet"
    assert a[1][1] == "gomjabar"

    a = http_auth_parse("HTTProxyAuth('param1')")
    assert len(a) == 2
    assert a[0] == 'HTTProxyAuth'
    assert len(a[1]) == 1
    assert a[1][0] == "param1"

def test_tokenize_word_list():
    twl = tokenize_word_list(["'s"])
    assert len(twl) == 1
    assert twl[0] == "'s"

@pytest.fixture
def hll_test_cases():
    return [
        ['Activision Blizzard Inc. — Mergers & Acquisition',['Microsoft','Blizzard','Activision','Inc']],
        ['Activision Blizzard Inc. — Mergers & Acquisition',['Microsoft','Blizzard','Activision','Inc.']],
        ['The same same word twice',['same']],
        ['Swirl_Pitch_1234412',['swirl']],
        ['Swirl Pitch 1234412',['swirl']],
        ['I love programming in Python',['programming', 'Python']],
        ['The quick brown fox jumps over the lazy dog',['quick', 'jumps', 'dog']],
        ['The weather is nice today',['rain', 'snow', 'sun']],
        ['ChatGPT is an AI language model', ['ChatGPT', 'AI', 'language', 'model']],
        ['This is a case insensitive test',["this", "Test"]],
        ["U.K. Blocks Microsoft's $69 Billion",["microsoft's"]]
    ]

@pytest.fixture
def hll_test_expected():
    return[
        '<em>Activision</em> <em>Blizzard</em> <em>Inc</em>. — Mergers & Acquisition',
        '<em>Activision</em> <em>Blizzard</em> <em>Inc</em>. — Mergers & Acquisition',
        'The same same word twice',
        '<em>Swirl</em>_Pitch_1234412',
        '<em>Swirl</em> Pitch 1234412',
        'I love <em>programming</em> in <em>Python</em>',
        'The <em>quick</em> brown fox <em>jumps</em> over the lazy <em>dog</em>',
        'The weather is nice today',
        '<em>ChatGPT</em> is an <em>AI</em> <em>language</em> <em>model</em>',
        'This is a case insensitive <em>test</em>',
        "U.K. Blocks <em>Microsoft's</em> $69 Billion"
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

@pytest.fixture
def test_suser_pw():
    return 'password'

def get_ddrp_suser(pw):
    return User.objects.create_user(
        username=''.join('test_ddrp_user'),
        password=pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

def get_dirp_suser(pw):
    dirp_uname = 'test_dirp_user'
    try:
        return User.objects.get(username=dirp_uname)
    except ObjectDoesNotExist:
        pass

    return User.objects.create_user(
        username=dirp_uname,
        password=pw,
        is_staff=True,  # Set to True if your view requires a staff user
        is_superuser=True,  # Set to True if your view requires a superuser
    )

def get_dirp_provider_data():
    return {
        "name": "test DDRP",
        "shared": True,
        "active": True,
        "default": True,
        "connector": "M365OutlookMessages",
        "url": "",
        "query_template": "{url}",
        "query_processor": "",
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "NOT=true,NOT_CHAR=-",
        "result_processor": "",
        "result_grouping_field":"conversationId",
        "result_processors": [
            "MappingResultProcessor",
            "DropIrrelevantPostResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "",
        "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
        "results_per_query": 10,
        "credentials": "",
        "eval_credentials": ""
    }


def create_dirp_provider(password):
    provider = get_dirp_provider_data()
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=get_dirp_suser(password))
    provider_id = serializer.data['id']
    return provider_id


def create_ddrp_provider(password):
    provider = get_ddrp_provider_data()
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=get_ddrp_suser(password))
    provider_id = serializer.data['id']
    return provider_id

def get_ddrp_provider_data():
    return {
        "name": "test DDRP",
        "shared": True,
        "active": True,
        "default": True,
        "connector": "M365OutlookMessages",
        "url": "",
        "query_template": "{url}",
        "query_processor": "",
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "NOT=true,NOT_CHAR=-",
        "result_processor": "",
        "result_grouping_field":"conversationId",
        "result_processors": [
            "MappingResultProcessor",
            "DedupeByFieldResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "",
        "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
        "results_per_query": 10,
        "credentials": "",
        "eval_credentials": ""
    }

def get_minimal_search_provider_data(name="test minimal search_provider", actve=True, default=True, tags=[]):
    return {
        "name": name,
        "shared": True,
        "active": actve,
        "default": default,
        "connector": "M365OutlookMessages",
        "url": "",
        "query_template": "{url}",
        "query_processor": "",
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "NOT=true,NOT_CHAR=-",
        "result_processor": "",
        "result_grouping_field":"conversationId",
        "result_processors": [
            "MappingResultProcessor",
            "DedupeByFieldResultProcessor"
        ],
        "response_mappings": "",
        "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.conversationId,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
        "results_per_query": 10,
        "credentials": "",
        "eval_credentials": "",
         "tags": tags
    }

@pytest.fixture
def match_all_test_cases_target():
    return [
        ['I', 'like', 'apple', 'banana', 'pie', 'with', 'banana'],
        ['I', 'have', 'a', 'bird', 'dog', 'he', 'is', 'a','swell', 'bird','dog']
    ]

@pytest.fixture
def match_all_test_cases_find():
    return [
        ['apple', 'banana'],
        ['bird', 'dog']
    ]


@pytest.fixture
def match_all_test_expected():
    return [
        [2],
        [3,9]
    ]

@pytest.mark.django_db
def test_match_all(match_all_test_cases_target, match_all_test_cases_find, match_all_test_expected):

    assert len(match_all_test_cases_target) == len(match_all_test_cases_find) == len(match_all_test_expected)

    for index, value in enumerate(match_all_test_cases_target):
        start_time = time.time()
        r = match_all(match_all_test_cases_find[index], (match_all_test_cases_target[index]))
        elapsed_time = time.time() - start_time
        assert r == match_all_test_expected[index]
        print(f"Elapsed time for index {index}: {elapsed_time} seconds")

def get_dirp_result():
    data_dir = os.path.dirname(os.path.abspath(__file__))
    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(data_dir, 'data', 'dirp-result.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data


@pytest.fixture
def ms_message_result_conversation():
    data_dir = os.path.dirname(os.path.abspath(__file__))
    # Build the absolute file path for the JSON file in the 'data' subdirectory
    json_file_path = os.path.join(data_dir, 'data', 'outlook_message_results.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    results = data.get('value')[0].get('hitsContainers')[0].get('hits')
    for i in results:
        i['conversationId'] = i['resource']['conversationId']
    return results

@pytest.mark.django_db
def test_select_providers_all_empty(test_suser_pw):
    pl = select_providers(providers=[],start_tag="", tags_in_query_list=[])
    assert len(pl) == 0


@pytest.mark.django_db
def test_select_providers_two_active_with_two_match_start_tag(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, True, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="foo", tags_in_query_list=[])
    assert len(pl) == 2

@pytest.mark.django_db
def test_select_providers_two_active_with_one_match_start_tag(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, True, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, True, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="foo", tags_in_query_list=[])
    assert len(pl) == 1

@pytest.mark.django_db
def test_select_providers_one_active_one_default_with_one_match_start_tag(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, False, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, True, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="foo", tags_in_query_list=[])
    assert len(pl) == 1

@pytest.mark.django_db
def test_select_providers_one_active_one_default_with_no_tags(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, False, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, True, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="", tags_in_query_list=[])
    assert len(pl) == 1

@pytest.mark.django_db
def test_select_providers_two_activ_with_misspelled_start_tag(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, True, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, True, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="xxx", tags_in_query_list=[])
    assert len(pl) == 2

@pytest.mark.django_db
def test_select_providers_two_activ_with_embedded_tag(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, True, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, False, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="xxx", tags_in_query_list=['bar'])
    assert len(pl) == 1

@pytest.mark.django_db
def test_select_providers_two_activ_with_embedded_tag_no_defaults(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, False, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, False, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="xxx", tags_in_query_list=['bar'])
    assert len(pl) == 1

@pytest.mark.django_db
def test_select_providers_two_active_with_embedded_no_start_tag_with_defaults(test_suser_pw):

    provider_list = []
    owner = get_ddrp_suser(test_suser_pw)
    provider = get_minimal_search_provider_data('active_default', True, True, ['foo'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    provider = get_minimal_search_provider_data('active_default', True, False, ['bar'])
    serializer = SearchProviderSerializer(data=provider)
    serializer.is_valid(raise_exception=True)
    serializer.save(owner=owner)
    provider_id = serializer.data['id']
    provider_list.append(SearchProvider.objects.get(pk=provider_id))

    pl = select_providers(providers=provider_list,start_tag="", tags_in_query_list=['bar'])
    assert len(pl) == 2

@pytest.mark.django_db
def test_dirp_result_processor(test_suser_pw):
    ## create a provider
    dirpp_id = create_dirp_provider(test_suser_pw)
    dirp_provider = SearchProvider.objects.get(pk=dirpp_id)

    ## create a search
    s = Search.objects.create(query_string='dirp',searchprovider_list=dirpp_id,owner=get_dirp_suser(test_suser_pw),status='POST_RESULT_PROCESSING',tags=[])
    s.save()
    dirp_json = get_dirp_result()
    result = Result.objects.create(owner=get_dirp_suser(test_suser_pw),
                                search_id=s,
                                provider_id=dirpp_id,
                                searchprovider='M365OutlookMessages',
                                query_string_to_provider='dirp',
                                query_to_provider='None',
                                status='READY',
                                retrieved=1,
                                found=1,
                                json_results=dirp_json,
                                time=1.9)
    result.save()
    n = 0
    ## test it
    dirp = DropIrrelevantPostResultProcessor(search_id=s.id)
    n = dirp.process()
    assert n == -3


@pytest.mark.django_db
def test_dd_result_processor(ms_message_result_conversation, test_suser_pw):
    ddrp_id = create_ddrp_provider(test_suser_pw)
    ddrp_provider = SearchProvider.objects.get(pk=ddrp_id)
    ddrp = DedupeByFieldResultProcessor(ms_message_result_conversation, ddrp_provider, "dune")
    r = ddrp.process()
    assert r
    assert len(ddrp.get_results()) == 1
    logger.debug(f'dedupped results {r}')

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

@pytest.mark.django_db
def test_cgptqp_1():
    tc = 'gig economy'
    expected = 'gig economy'
    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance
        cgptqp = GenAIQueryProcessor(
            tc,
            '',
            ["PROMPT:Write a more precise query of similar length to this : {query_string}",]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        mock_create.assert_called_once_with(
            model=TEST_AI_MODEL,
            messages=[
                {"role": "system", "content": "You are helping a user formulate better queries"},
                {"role": "user", "content": "Write a more precise query of similar length to this : gig economy"}
            ],
            temperature=0
        )

@pytest.mark.django_db
def test_cgptqp_2():
    tc = 'gig economy'
    expected = 'gig economy'

    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance
        cgptqp = GenAIQueryProcessor(tc,
            '',
            ["PROMPT:Write a more precise query of similar length to this : {query_string}",
             "CHAT_QUERY_REWRITE_GUIDE:You are a malevolent dictator"]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        mock_create.assert_called_once_with(model=TEST_AI_MODEL, messages=[
                {"role": "system", "content": "You are a malevolent dictator"},
                {"role": "user", "content":   "Write a more precise query of similar length to this : gig economy"}
            ],
            temperature=0)

@pytest.mark.django_db
def test_cgptqp_3():
    tc = 'gig economy'
    expected = 'gig economy'

    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance
        cgptqp = GenAIQueryProcessor(tc,
            '',
            ["CHAT_QUERY_REWRITE_PROMPT:Write a more precise query of similar length to this : {query_string}",
             "CHAT_QUERY_REWRITE_GUIDE:You are a malevolent dictator"]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        mock_create.assert_called_once_with(model=TEST_AI_MODEL, messages=[
                {"role": "system", "content": "You are a malevolent dictator"},
                {"role": "user", "content":   "Write a more precise query of similar length to this : gig economy"}
            ],
            temperature=0)

@pytest.mark.django_db
def test_cgptqp_4():
    tc = 'gig economy'
    expected = 'gig economy'

    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance

        cgptqp = GenAIQueryProcessor(tc,
            '',
            ["PROMPT:This should be used: {query_string}",
             "CHAT_QUERY_REWRITE_PROMPT:Write a more precise query of similar length to this : {query_string}",
             "CHAT_QUERY_REWRITE_GUIDE:You are a malevolent dictator"]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        mock_create.assert_called_once_with(model=TEST_AI_MODEL, messages=[
                {"role": "system", "content": "You are a malevolent dictator"},
                {"role": "user", "content":   "This should be used: gig economy"}
            ],
            temperature=0)


@pytest.mark.django_db
def test_cgptqp_5():
    tc = 'gig economy'
    expected = 'Gig economy large scale economics'

    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance

        cgptqp = GenAIQueryProcessor(tc,
            '',
            ["PROMPT:This should be used: {query_string}",
             "CHAT_QUERY_REWRITE_PROMPT:Write a more precise query of similar length to this : {query_string}",
             "CHAT_QUERY_REWRITE_GUIDE:You are a malevolent dictator",
             "CHAT_QUERY_DO_FILTER:False"]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        assert not cgptqp.do_filter
        mock_create.assert_called_once_with(model=TEST_AI_MODEL, messages=[
                {"role": "system", "content": "You are a malevolent dictator"},
                {"role": "user", "content":   "This should be used: gig economy"}
            ],
            temperature=0)


@pytest.mark.django_db
def test_cgptqp_6():
    tc = 'gig economy'
    expected = 'gig economy'

    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance

        cgptqp = GenAIQueryProcessor(tc,
            '',
            ["PROMPT:This should be used: {query_string}",
             "CHAT_QUERY_REWRITE_PROMPT:Write a more precise query of similar length to this : {query_string}",
             "CHAT_QUERY_REWRITE_GUIDE:You are a malevolent dictator",
             "CHAT_QUERY_DO_FILTER:True"]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        assert cgptqp.do_filter
        mock_create.assert_called_once_with(model=TEST_AI_MODEL, messages=[
                {"role": "system", "content": "You are a malevolent dictator"},
                {"role": "user", "content":   "This should be used: gig economy"}
            ],
            temperature=0)


@pytest.mark.django_db
def test_cgptqp_7():
    tc = 'gig economy'
    expected = 'gig economy'

    with mock.patch('openai.OpenAI') as mock_openai:
        client_instance = mock.MagicMock()
        mock_openai.return_value = client_instance
        mock_create = mock.MagicMock()
        mock_create.return_value.choices[0].message.content = "Gig economy large scale economics"
        client_instance.chat.completions.create = mock_create
        mock_swirlai_client = mock.MagicMock()
        mock_swirlai_client.get_model = mock.MagicMock()
        mock_swirlai_client.get_model.return_value = 'fake-model'
        mock_swirlai_client.openai_client = client_instance

        cgptqp = GenAIQueryProcessor(tc,
            '',
            ["PROMPT:This should be used: {query_string}",
             "CHAT_QUERY_REWRITE_PROMPT:Write a more precise query of similar length to this : {query_string}",
             "CHAT_QUERY_REWRITE_GUIDE:You are a malevolent dictator",
             "CHAT_QUERY_DO_FILTER:xxx"]
        )
        actual = cgptqp.process(client=mock_swirlai_client)
        assert actual == expected
        assert cgptqp.do_filter == MODEL_DEFAULT_DO_FILTER
        mock_create.assert_called_once_with(model=TEST_AI_MODEL, messages=[
                {"role": "system", "content": "You are a malevolent dictator"},
                {"role": "user", "content":   "This should be used: gig economy"}
            ],
            temperature=0)


@pytest.fixture
def rm_url_encoder_test_cases():
    return {
        'foo':'bar',
        'sw_urlencode(bar)':'baz',
        'sw_urlencode(yyz)':'foo==',
        'sw_urlencode(yyz':'foo==',
        'foo(yyz)':'foo==',
        'sw_urlencode(hitId)':'askjfasdkj,,l::":kajsdf==alksfja;lkdjs===',
        'sw_urlencode(slashes)':'askjfasdkj,,l::":kajsdf//alksfja;lkdjs==='
    }

@pytest.fixture
def rm_url_encoder_test_expected():
    return {
        'foo':{'key':'foo', 'value':'bar'},
        'sw_urlencode(bar)':{'key':'bar', 'value':'baz'},
        'sw_urlencode(yyz)':{'key':'yyz', 'value':'foo%3D%3D'},
        'sw_urlencode(yyz': {'key':'sw_urlencode(yyz', 'value':'foo=='},
        'foo(yyz)': {'key':'foo(yyz)', 'value':'foo=='},
        'sw_urlencode(hitId)': {'key':'hitId', 'value':'askjfasdkj%2C%2Cl%3A%3A%22%3Akajsdf%3D%3Dalksfja%3Blkdjs%3D%3D%3D'},
        'sw_urlencode(slashes)':{'key':'slashes', 'value':'askjfasdkj%2C%2Cl%3A%3A%22%3Akajsdf%2F%2Falksfja%3Blkdjs%3D%3D%3D'}
    }

@pytest.mark.django_db
def test_rm_url_encoder(rm_url_encoder_test_cases, rm_url_encoder_test_expected):
    for k in rm_url_encoder_test_cases.keys():
        uc  = ResultMapConverter(k)
        assert uc.get_key() == rm_url_encoder_test_expected[k].get('key')
        assert uc.get_value(rm_url_encoder_test_cases.get(k)) == rm_url_encoder_test_expected[k].get('value')

    # Boundary cases:
    uc  = ResultMapConverter(None)
    k = uc.get_key()
    v = uc.get_value('foo')
    assert k == None
    assert v == 'foo'

    uc  = ResultMapConverter('')
    k = uc.get_key()
    v = uc.get_value('foo')
    assert k == ''
    assert v == 'foo'

@pytest.fixture
def rm_btc_converter_test_cases():
    return {
        'sw_btcconvert(foo)': '100000000',  # Represents 1 BTC in satoshis
        'bar': '200000000',  # Represents 2 BTC in satoshis
        'sw_btcconvert(baz)': '100',  # Represents 0.000001 BTC in satoshis
        'sw_btcconvert(waldo)': '12345678',  # Represents 0.12345678 BTC in satoshis
        'sw_btcconvert(fred)': '50000000',  # Represents 0.5 BTC in satoshis
    }

@pytest.fixture
def rm_btc_converter_test_expected():
    return {
        'sw_btcconvert(foo)': {'key': 'foo', 'value': '1'},
        'bar': {'key': 'bar', 'value': '200000000'},  # This value won't be converted since there's no directive
        'sw_btcconvert(baz)': {'key': 'baz', 'value': '0.000001'},
        'sw_btcconvert(waldo)': {'key': 'waldo', 'value': '0.12345678'},
        'sw_btcconvert(fred)': {'key': 'fred', 'value': '0.5'}
    }

@pytest.mark.django_db
def test_rm_btc_converter(rm_btc_converter_test_cases, rm_btc_converter_test_expected):
    for k, v in rm_btc_converter_test_cases.items():
        converter = ResultMapConverter(k)
        assert converter.get_key() == rm_btc_converter_test_expected[k]['key']
        assert converter.get_value(v) == rm_btc_converter_test_expected[k]['value']

# Boundary cases
@pytest.mark.django_db
def test_rm_btc_converter_boundary_cases():
    # Test for None key
    converter = ResultMapConverter(None)
    assert converter.get_key() == None
    assert converter.get_value('foo') == 'foo'

    # Test for empty string key
    converter = ResultMapConverter('')
    assert converter.get_key() == ''
    assert converter.get_value('foo') == 'foo'

    # Test for the directive but missing parens
    converter = ResultMapConverter('sw_btcconvertfoo')
    assert converter.get_key() == 'sw_btcconvertfoo'
    assert converter.get_value('foo') == 'foo'

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
    return ['2008','1681393728.832229','1681393728','Jan 17, 1975']

@pytest.fixture
def utils_date_str_to_timestamp_expected():
    return['2008-01-01 00:00:00','2023-04-13 09:48:48.832229','2023-04-13 09:48:48','1975-01-17 00:00:00']

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
    assert response.status_code == 200, 'Expected HTTP status code 200'
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
