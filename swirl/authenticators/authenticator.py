from django.http import HttpResponseRedirect
from datetime import datetime

class Authenticator:

    type = "SWIRL Authenticator"
    
    ########################################        

    def get_session_data(self, request):
        if 'user' in request.session:
            if self.expires_in_field in request.session['user']:
                return request.session['user']
            return False
        return False

    def set_session_data(self, request, access_token, refresh_token, expiration_time):
        if 'user' not in request.session:
            request.session['user'] = {
                self.access_token_field: access_token,
                self.refresh_token_field: refresh_token,
                self.expires_in_field: expiration_time
            }
        else:
            request.session['user'][self.access_token_field] = access_token
            request.session['user'][self.refresh_token_field] = refresh_token
            request.session['user'][self.expires_in_field] = expiration_time

    def get_auth_app(self, request):
        return {}

    def is_authenticated(self, session_data):
        try:
            now = datetime.now()
            if self.expires_in_field in session_data:
                if session_data[self.expires_in_field] > int(now.timestamp()):
                    return True
                return False
            return False
        except:
            return False

    def login(request):
        return HttpResponseRedirect('http://example.com')

    def callback(request):
        return HttpResponseRedirect('/swirl/')