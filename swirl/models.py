'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django.db import models
from django.urls import reverse

def getSearchProviderQueryProcessorsDefault():
    return ["AdaptiveQueryProcessor"]

def getSearchProviderResultProcessorsDefault():
    return ["MappingResultProcessor"]


class SearchProvider(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    shared = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    default = models.BooleanField(default=True)
    CONNECTOR_CHOICES = [
        ('RequestsGet', 'HTTP/GET returning JSON'),
        ('Elastic', 'Elasticsearch Query String'),
        # Uncomment the line below to enable PostgreSQL
        # ('PostgreSQL', 'PostgreSQL'),
        ('BigQuery', 'Google BigQuery'),
        ('Sqlite3', 'Sqlite3')
    ]
    connector = models.CharField(max_length=200, default='RequestsGet', choices=CONNECTOR_CHOICES)
    url = models.CharField(max_length=2048, default=str, blank=True)
    query_template = models.CharField(max_length=2048, default='{url}?q={query_string}', blank=True)
    QUERY_PROCESSOR_CHOICES = [
        ('GenericQueryProcessor', 'GenericQueryProcessor'),
        ('TestQueryProcessor', 'TestQueryProcessor'),
        ('AdaptiveQueryProcessor', 'AdaptiveQueryProcessor'),
        ('SpellcheckQueryProcessor', 'SpellcheckQueryProcessor (TextBlob)')
    ]
    query_processor = models.CharField(max_length=200, default='', choices=QUERY_PROCESSOR_CHOICES, blank=True)
    query_processors = models.JSONField(default=getSearchProviderQueryProcessorsDefault, blank=True)
    query_mappings = models.CharField(max_length=2048, default=str, blank=True)
    RESULT_PROCESSOR_CHOICES = [
        ('GenericResultProcessor', 'GenericResultProcessor'),
        ('DuplicateHalfResultProcessor', 'DuplicateHalfResultProcessor'),
        ('TestResultProcessor', 'TestResultProcessor'),
        ('MappingResultProcessor', 'MappingResultProcessor')
    ]
    response_mappings = models.CharField(max_length=2048, default=str, blank=True)
    result_processor = models.CharField(max_length=200, default='MappingResultProcessor', choices=RESULT_PROCESSOR_CHOICES, blank=True)
    result_processors = models.JSONField(default=getSearchProviderResultProcessorsDefault, blank=True)
    result_mappings = models.CharField(max_length=2048, default=str, blank=True)
    results_per_query = models.IntegerField(default=10)
    credentials = models.CharField(max_length=512, default=str, blank=True)
    tags = models.JSONField(default=list)

    class Meta:
        ordering = ['id']

    def get_absolute_url(self):
        # Returns the URL to access
        return reverse('model-detail-view', args=[str(self.id)])

    def __str__(self):
        return self.name


def getSearchPostResultProcessorsDefault():
    return ["DedupeByFieldPostResultProcessor","CosineRelevancyPostResultProcessor"]

class Search(models.Model):
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    query_string = models.CharField(max_length=256, default=str)
    query_string_processed = models.CharField(max_length=256, default=str, blank=True)
    SORT_CHOICES = [
        ('relevancy', 'relevancy'),
        ('date', 'date')
    ]
    sort = models.CharField(max_length=50, default='relevancy', blank=True)
    results_requested = models.IntegerField(default=10)
    searchprovider_list = models.JSONField(default=list, blank=True)
    subscribe = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default='NEW_SEARCH')
    time = models.FloatField(default=0.0)
    PRE_QUERY_PROCESSOR_CHOICES = [
        ('GenericQueryProcessor', 'GenericQueryProcessor'),
        ('TestQueryProcessor', 'TestQueryProcessor'),
        ('SpellcheckQueryProcessor', 'SpellcheckQueryProcessor (TextBlob)')
    ]
    pre_query_processor = models.CharField(max_length=200, default=str, blank=True, choices=PRE_QUERY_PROCESSOR_CHOICES)
    pre_query_processors = models.JSONField(default=list, blank=True)
    POST_RESULT_PROCESSOR_CHOICES = [
        ('DedupeByFieldPostResultProcessor', 'DedupeByFieldPostResultProcessor'),
        ('DedupeBySimilarityPostResultProcessor', 'DedupeBySimilarityPostResultProcessor'),
        ('CosineRelevancyPostResultProcessor', 'CosineRelevancyPostResultProcessor (w/spaCy)')
    ]
    post_result_processor = models.CharField(max_length=200, default='', blank=True, choices=POST_RESULT_PROCESSOR_CHOICES)
    post_result_processors = models.JSONField(default=getSearchPostResultProcessorsDefault, blank=True)
    result_url = models.CharField(max_length=2048, default='/swirl/results?search_id=%d&result_mixer=%s', blank=True)
    new_result_url = models.CharField(max_length=2048, default='/swirl/results?search_id=%d&result_mixer=RelevancyNewItemsMixer', blank=True)
    messages = models.JSONField(default=list, blank=True)
    MIXER_CHOICES = [
        ('RelevancyMixer', 'RelevancyMixer'),
        ('RelevancyNewItemsMixer', 'RelevancyNewItemsMixer'),
        ('RoundRobinMixer', 'RoundRobinMixer'),
        ('Stack1Mixer', 'Stack1Mixer'),
        ('Stack2Mixer', 'Stack2Mixer'),
        ('Stack3Mixer', 'Stack3Mixer'),
        ('StackNMixer', 'StackNMixer'),
        ('DateMixer', 'DateMixer'),
        ('DateNewItemsMixer', 'DateNewItemsMixer')
    ]
    result_mixer = models.CharField(max_length=200, default='RelevancyMixer', choices=MIXER_CHOICES)
    RETENTION_CHOICES = [
        (0, 'Never expire'),
        (1, 'Expire after 1 hour'),
        (2, 'Expire after 1 day'),
        (3, 'Expire after 1 month')
    ]
    retention = models.IntegerField(default=0, choices=RETENTION_CHOICES)
    tags = models.JSONField(default=list)

    class Meta:
        ordering = ['-date_updated']

    def get_absolute_url(self):
        # Returns the URL to access
        return reverse('model-detail-view', args=[str(self.id)])

    def __str__(self):
        signature = str(self.id) + ':' + str(self.searchprovider_list) + ':' + self.query_string
        return signature
        
class Result(models.Model):
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    search_id = models.ForeignKey(Search, on_delete=models.CASCADE) 
    provider_id = models.IntegerField(default=0)
    searchprovider = models.CharField(max_length=50, default=str)
    query_string_to_provider = models.CharField(max_length=256, default=str)
    query_to_provider = models.CharField(max_length=2048, default=str)
    query_processors = models.JSONField(default=list, blank=True)
    result_processors = models.JSONField(default=list, blank=True)
    messages = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default=str)
    retrieved = models.IntegerField(default=0)
    found = models.IntegerField(default=0)
    time = models.FloatField(default=0.0)
    json_results = models.JSONField(default=list)
    tags = models.JSONField(default=list)

    class Meta:
        ordering = ['-date_updated']

    def get_absolute_url(self):
        # Returns the URL to access
        return reverse('model-detail-view', args=[str(self.id)])

    def __str__(self):
        signature = str(self.id) + ':' + str(self.search_id) + ':' + str(self.searchprovider)
        return signature
