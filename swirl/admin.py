from django.contrib import admin
from .models import SearchProvider, Search, Result, QueryTransform, MicrosoftToken

admin.site.site_header = 'Swirl Metasearch' # title
admin.site.index_title = 'Administration Console' # subtitle
# admin page is index_title | site_title
admin.site.site_title = 'Swirl Metasearch'

admin.site.register(SearchProvider)
admin.site.register(Search)
admin.site.register(Result)
admin.site.register(QueryTransform)
admin.site.register(MicrosoftToken)
