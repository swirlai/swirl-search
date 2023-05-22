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
from swirl.authenticators import Microsoft

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'searchproviders', views.SearchProviderViewSet, basename='searchproviders')
router.register(r'querytransforms', views.QueryTransformViewSet, basename='querytransforms')
router.register(r'search', views.SearchViewSet, basename='search')
router.register(r'results', views.ResultViewSet, basename='results')

router.register(r'sapi/search', views.SearchViewSet, basename='spyglass-search')
router.register(r'sapi/results', views.ResultViewSet, basename='spyglass-results')
router.register(r'sapi/authenticators', views.AuthenticatorViewSet, basename='spyglass-authenticators')
router.register(r'sapi/searchproviders', views.SearchProviderViewSet, basename='spyglass-searchproviders'),

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
    path('query_transform_form/', views.query_transform_form, name='query_transform_form'),

    # this appears to be necessary to access the view from a pytest API unit test
    path('querytransforms/list', views.QueryTransformViewSet.as_view({'get': 'list'}), name='querytransforms/list'),
    path('querytransforms/create', views.QueryTransformViewSet.as_view({'post': 'create'}), name='create'),
    path('querytransforms/retrieve/<int:pk>/', views.QueryTransformViewSet.as_view({'get': 'retrieve'}), name='retrieve'),
    path('querytransforms/update/<int:pk>/', views.QueryTransformViewSet.as_view({'put': 'update'}), name='update'),
    path('querytransforms/delete/<int:pk>/', views.QueryTransformViewSet.as_view({'delete': 'destroy'}), name='delete'),

    path('search/search', views.SearchViewSet.as_view({'get': 'list'}), name='search'),

    path('', views.index, name='index'),
    path('index.html', views.index, name='index'),
    path('error.html', views.error, name='error'),
    path('search.html', views.search, name='search_form'),
    path('authenticators.html', views.authenticators, name='authenticators'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('microsoft-callback', Microsoft().callback, name='microsoft_callback'),
    path('register/', views.registration, name='register'),
    path('register/confirm/<str:token>/<str:signature>/', views.registration_confirmation, name='registration_confirmation'),
    path('register/confirm_sent/', views.registration_confirmation_sent, name='registration_confirmation_sent'),

    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),


    path('', include(router.urls)),
]
