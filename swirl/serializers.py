'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from swirl.models import SearchProvider, Search, Result,QueryTransform

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']

class SearchProviderSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = SearchProvider
        fields = ['id', 'name', 'owner', 'shared', 'date_created', 'date_updated', 'active', 'default', 'connector', 'url', 'query_template', 'query_processors', 'query_mappings', 'result_processors', 'response_mappings', 'result_mappings', 'results_per_query', 'credentials', 'eval_credentials', 'tags']

class SearchProviderNoCredentialsSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = SearchProvider
        fields = ['id', 'name', 'owner', 'shared', 'date_created', 'date_updated', 'active', 'default', 'connector', 'url', 'query_template', 'query_processors', 'query_mappings', 'result_processors', 'response_mappings', 'result_mappings', 'results_per_query', 'tags']

class SearchSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Search
        fields = ['id', 'owner', 'date_created', 'date_updated', 'query_string', 'query_string_processed', 'sort', 'results_requested', 'searchprovider_list', 'subscribe', 'status', 'pre_query_processors', 'post_result_processors', 'result_url', 'new_result_url', 'messages', 'result_mixer', 'retention', 'tags']

class ResultSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Result
        fields = ['id', 'owner', 'date_created', 'date_updated', 'search_id', 'searchprovider', 'query_to_provider', 'query_processors', 'result_processors', 'result_processor_json_feedback', 'messages', 'status', 'retrieved', 'found', 'time', 'json_results', 'tags']

class QueryTransformSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = QueryTransform
        fields = ['id', 'name','owner','shared','date_created','date_updated','qrx_type','config_content']

class QueryTrasnformNoCredentialsSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = QueryTransform
        fields = ['id', 'name','owner','shared', 'date_created','date_updated','qrx_type','config_content']
