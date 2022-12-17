'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from swirl.models import SearchProvider, Search, Result

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
        fields = ['id', 'name', 'owner', 'shared', 'date_created', 'date_updated', 'active', 'default', 'connector', 'url', 'query_template', 'query_processor', 'query_mappings', 'result_processor', 'response_mappings', 'result_mappings', 'results_per_query', 'credentials', 'tags']

class SearchSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Search
        fields = ['id', 'owner', 'date_created', 'date_updated', 'query_string', 'query_string_processed', 'sort', 'results_requested', 'searchprovider_list', 'subscribe', 'status', 'pre_query_processor', 'post_result_processor', 'result_url', 'new_result_url', 'messages', 'result_mixer', 'retention', 'tags']

class ResultSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Result
        fields = ['id', 'owner', 'date_created', 'date_updated', 'search_id', 'searchprovider', 'query_to_provider', 'result_processor', 'messages', 'retrieved', 'found', 'time', 'json_results', 'tags']