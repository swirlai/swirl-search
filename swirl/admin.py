from django.contrib import admin

# Register your models here.

from .models import SearchProvider, Search, Result

admin.site.register(SearchProvider)
admin.site.register(Search)
admin.site.register(Result)
