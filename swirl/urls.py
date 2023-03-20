'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    SWIRL 1.x
'''

# from webbrowser import get
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'searchproviders', views.SearchProviderViewSet, basename='searchproviders')
router.register(r'search', views.SearchViewSet, basename='search')
router.register(r'results', views.ResultViewSet, basename='results')

urlpatterns = [
    path('openapi', get_schema_view(
            title="SWIRL Swagger",
            description="SWIRL API descriptions",
            version="1.1.0"
        ), name='openapi-schema'),
    path('swagger-ui/', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url':'openapi-schema'}
    ), name='swagger-ui'),
    path('', views.index, name='index'),
    path('index.html', views.index, name='index'),
    path('error.html', views.error, name='error'),
    path('search.html', views.search, name='search_form'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('register/', views.registration, name='register'),
    path('register/confirm/<str:token>/<str:signature>/', views.registration_confirmation, name='registration_confirmation'),
    path('register/confirm_sent/', views.registration_confirmation_sent, name='registration_confirmation_sent'),
    path('', include(router.urls)),
]
