from django.http import HttpResponseRedirect
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

# Key in the session's token data naming the user it was stored for.
SESSION_OWNER_FIELD = 'owner_id'

class Authenticator:

    type = "SWIRL Authenticator"

    def __init__(self):
        self.access_token_field = ''
        self.refresh_token_field = ''
        self.expires_in_field = ''

    ########################################

    def _session_owner_id(self, request):
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            return user.id
        return None

    def get_session_data(self, request):
        """The token data kept in this browser session, when it was stored for
        the user making the request. A session can outlive a sign-out, so data
        stored for another user, or for nobody, is not returned."""
        if 'user' not in request.session:
            return False
        data = request.session['user']
        owner_id = self._session_owner_id(request)
        if owner_id is None or data.get(SESSION_OWNER_FIELD) != owner_id:
            return False
        return data

    def get_access_token_session_field(self):
        return self.access_token_field

    def get_refresh_token_session_field(self):
        return self.refresh_token_field

    def get_access_token_expiration_time_session_field(self):
        return self.expires_in_field

    def set_session_data(self, request, access_token, refresh_token, expiration_time):
        owner_id = self._session_owner_id(request)
        current = request.session.get('user')
        if not current or current.get(SESSION_OWNER_FIELD) != owner_id:
            # Nothing stored yet, or stored for a different user: start clean
            # so one user's tokens are never mixed with another's.
            request.session['user'] = {SESSION_OWNER_FIELD: owner_id}
        request.session['user'][self.access_token_field] = access_token
        request.session['user'][self.refresh_token_field] = refresh_token
        request.session['user'][self.expires_in_field] = expiration_time
        request.session.save()

    def get_auth_app(self, request):
        return {}

    def is_authenticated(self, session_data):
        try:
            now = datetime.now()
            if self.expires_in_field in session_data:
                if session_data[self.expires_in_field] > int(now.timestamp()):
                    return True
                logger.warning(
                    f'{self.type}: token expired '
                    f'({self.expires_in_field}={session_data[self.expires_in_field]} '
                    f'<= now={int(now.timestamp())})'
                )
                return False
            logger.warning(
                f'{self.type}: {self.expires_in_field!r} not in session_data; '
                f'auth header likely missing from the search request '
                f'(keys present: {list(session_data.keys()) if hasattr(session_data, "keys") else type(session_data).__name__})'
            )
            return False
        except Exception as err:
            logger.warning(f'{self.type}: is_authenticated() raised {type(err).__name__}: {err}')
            return False

    def login(self, request):
        return HttpResponseRedirect('http://example.com')

    def callback(self, request):
        return HttpResponseRedirect('/swirl/')

    def update_token(self, request):
        return {}