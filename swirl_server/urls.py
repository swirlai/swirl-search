"""swirl_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.conf import settings
from django.contrib import admin
from django.views.static import serve
from django.urls import include, path, re_path
from django.shortcuts import redirect

urlpatterns = [
    re_path('galaxy', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'static'),
        'path': 'galaxy/index.html',
    }),
    path('swirl/', include('swirl.urls')),
    path('api/swirl/', include('swirl.urls')),
    path('', lambda req: redirect('/galaxy/')),
    path('admin/', admin.site.urls)
]
