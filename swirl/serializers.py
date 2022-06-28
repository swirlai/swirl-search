'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from django.contrib.auth.models import User, Group
from swirl.models import SearchProvider, Search, Result
from rest_framework import serializers

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']

class SearchProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchProvider
        fields = ['id', 'active', 'date_created', 'date_updated', 'name', 'connector', 'url', 'query_template', 'query_processor', 'query_mappings', 'result_processor', 'result_mappings', 'results_per_query', 'credentials']

class SearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Search
        fields = ['id', 'date_created', 'date_updated', 'query_string', 'query_string_processed', 'sort', 'results_requested', 'searchprovider_list', 'status', 'pre_query_processor', 'post_result_processor', 'result_url', 'messages', 'result_mixer', 'retention' ]

class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ['id', 'date_created', 'search_id', 'searchprovider', 'query_to_provider', 'result_processor', 'messages', 'retrieved', 'found', 'json_results']