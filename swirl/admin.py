from django.contrib import admin
from .models import SearchProvider, Search, Result

admin.site.site_title = 'SWIRL SEARCH'
admin.site.site_header = 'Administration Console'
admin.site.index_title = 'SWIRL SEARCH'

admin.site.register(SearchProvider)
admin.site.register(Search)
admin.site.register(Result)
