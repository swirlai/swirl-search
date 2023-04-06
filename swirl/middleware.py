from rest_framework.authtoken.models import Token
from django.http import HttpResponseForbidden

class TokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.path == '/swirl/login/' or '/api/' not in request.path:
            return self.get_response(request)
        if 'Authorization' not in request.headers:
            return HttpResponseForbidden()
        
        auth_header = request.headers['Authorization']
        token = auth_header.split(' ')[1]
        try:
            Token.objects.get(key=token)
        except Token.DoesNotExist:
            return HttpResponseForbidden()
        
        return self.get_response(request)
