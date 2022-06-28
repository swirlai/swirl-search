'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from django.db import models

# Create your models here.

class SearchProvider(models.Model):
    id = models.BigAutoField(primary_key=True)
    active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=200)
    CONNECTOR_CHOICES = [
        ('requests_get', 'requests_get'),
        ('elastic', 'elasticsearch queryString'),
        ('sqlite3', 'sqlite3')
    ]
    connector = models.CharField(max_length=200, default='requests_get', choices=CONNECTOR_CHOICES)
    url = models.CharField(max_length=1024, default=str, blank=True)
    query_template = models.CharField(max_length=200, default='{url}?q={query_string}')
    QUERY_PROCESSOR_CHOICES = [
        ('generic_query_processor', 'generic_query_processor'),
        ('spellcheck_query_processor', 'spellcheck_query_processor (TextBlob)')
    ]
    query_processor = models.CharField(max_length=200, default='generic_query_processor', choices=QUERY_PROCESSOR_CHOICES)
    query_mappings = models.CharField(max_length=200, default=str, blank=True)
    RESULT_PROCESSOR_CHOICES = [
        ('generic_result_processor', 'generic_result_processor'),
        ('swirl_result_matches_processor', 'swirl_result_matches_processor')
    ]
    result_processor = models.CharField(max_length=200, default='generic_result_processor', choices=RESULT_PROCESSOR_CHOICES)
    result_mappings = models.CharField(max_length=200, default=str, blank=True)
    results_per_query = models.IntegerField(default=10)
    credentials = models.CharField(max_length=200, default=str, blank=True)
        
    def __str__(self):
        return self.name

class Search(models.Model):
    id = models.BigAutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    query_string = models.CharField(max_length=200, default=str)
    query_string_processed = models.CharField(max_length=200, default=str, blank=True)
    SORT_CHOICES = [
        ('relevancy', 'relevancy'),
        ('date', 'date')
    ]
    sort = models.CharField(max_length=50, default='relevancy', blank=True)
    results_requested = models.IntegerField(default=10)
    searchprovider_list = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=50, default='NEW_SEARCH')
    PRE_QUERY_PROCESSOR_CHOICES = [
        ('generic_pre_query_processor', 'generic_pre_query_processor'),
        ('spellcheck_query_processor', 'spellcheck_query_processor (TextBlob)')
    ]
    pre_query_processor = models.CharField(max_length=200, default=str, blank=True, choices=PRE_QUERY_PROCESSOR_CHOICES)
    POST_RESULT_PROCESSOR_CHOICES = [
        ('generic_post_result_processor', 'generic_post_result_processor'),
        ('generic_relevancy_processor', 'generic_relevancy_processor'),
        ('cosine_relevancy_processor', 'cosine_relevancy_processor (spaCy)')
    ]
    post_result_processor = models.CharField(max_length=200, default='cosine_relevancy_processor', blank=True, choices=POST_RESULT_PROCESSOR_CHOICES)
    result_url = models.CharField(max_length=200, default='/swirl/results?search_id=%d&result_mixer=%s', blank=True)
    messages = models.JSONField(default=list, blank=True)
    MIXER_CHOICES = [
        ('relevancy_mixer', 'relevancy_mixer'),
        ('round_robin_mixer', 'round_robin_mixer'),
        ('stack_mixer', 'stack_mixer'),
        ('stack_2_mixer', 'stack_2_mixer'),
        ('stack_3_mixer', 'stack_3_mixer')
    ]
    result_mixer = models.CharField(max_length=200, default='relevancy_mixer', choices=MIXER_CHOICES)
    RETENTION_CHOICES = [
        (0, 'Do not expire'),
        (1, 'Expire after 1 hour'),
        (2, 'Expire after 1 day'),
        (3, 'Expire after 1 month')
    ]
    retention = models.IntegerField(default=0, choices=RETENTION_CHOICES)

    def __str__(self):
        signature = str(self.id) + ':' + str(self.searchprovider_list) + ':' + self.query_string
        return signature

class Result(models.Model):
    id = models.BigAutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    search_id = models.ForeignKey(Search, on_delete=models.CASCADE) 
    searchprovider = models.CharField(max_length=50, default=str)
    query_to_provider = models.CharField(max_length=200, default=str)
    result_processor = models.CharField(max_length=200, default=str)
    messages = models.JSONField(default=list, blank=True)
    retrieved = models.IntegerField(default=0)
    found = models.IntegerField(default=0)
    json_results = models.JSONField(default=list)

    def __str__(self):
        signature = str(self.id) + ':' + str(self.search) + ':' + str(self.searchprovider)
        return signature
