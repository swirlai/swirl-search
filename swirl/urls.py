'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    Swirl 1.x
'''

# from webbrowser import get
from django.urls import include, path
from rest_framework import routers, permissions
from . import views
from swirl.authenticators import Microsoft
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'searchproviders', views.SearchProviderViewSet, basename='searchproviders')
router.register(r'querytransforms', views.QueryTransformViewSet, basename='querytransforms')
router.register(r'search', views.SearchViewSet, basename='search')
router.register(r'results', views.ResultViewSet, basename='results')

router.register(r'sapi/search', views.SearchViewSet, basename='galaxy-search')
router.register(r'sapi/results', views.ResultViewSet, basename='galaxy-results')
router.register(r'sapi/authenticators', views.AuthenticatorViewSet, basename='galaxy-authenticators')
router.register(r'sapi/searchproviders', views.SearchProviderViewSet, basename='galaxy-searchproviders'),

schema_view = get_schema_view(
    openapi.Info(
        title="Swirl Swagger",
        default_version="v1",
        description="Swirl API descriptions",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('swagger/', schema_view.with_ui(cache_timeout=0),
         name='schema-swagger-ui'),
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
    path('authenticators.html', views.authenticators, name='authenticators'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('microsoft-callback', Microsoft().callback, name='microsoft_callback'),
    path('register/', views.registration, name='register'),
    path('register/confirm/<str:token>/<str:signature>/', views.registration_confirmation, name='registration_confirmation'),
    path('register/confirm_sent/', views.registration_confirmation_sent, name='registration_confirmation_sent'),

    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('oidc_authenticate/', views.OidcAuthView.as_view()),
    path('microsoft/update_token', views.UpdateMicrosoftToken.as_view()),


    path('', include(router.urls)),
]
