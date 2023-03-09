import msal
from django.http import HttpResponseRedirect
import requests
import json
from datetime import datetime, timedelta

scopes = ["User.Read", "Mail.Read", "Files.Read.All", "Calendars.Read", "Sites.Read.All"]

graph_url = 'https://graph.microsoft.com/v1.0'

def _test_get_outlook_messages(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = "https://graph.microsoft.com/v1.0/me/messages?$select=subject,bodyPreview,from,receivedDateTime"
    response = requests.get(url, headers=headers)
    messages = json.loads(response.content.decode("utf-8"))

def get_session_data(request):
    if 'user' in request.session:
        if 'microsoft_access_token_expiration_time' in request.session['user']:
            return request.session['user']
        return False
    return False

def set_session_data(request, access_token, refresh_token, expiration_time):
    if 'user' not in request.session:
        request.session['user'] = {
            'microsoft_access_token': access_token,
            'microsoft_refresh_token': refresh_token,
            'microsoft_access_token_expiration_time': expiration_time
        }
    else:
        request.session['user']['microsoft_access_token'] = access_token
        request.session['user']['microsoft_refresh_token'] = refresh_token
        request.session['user']['microsoft_access_token_expiration_time'] = expiration_time
    # print('session obj:', request.session['user'])

def get_user(token):
    # Send GET to /me
    user = requests.get('{0}/me'.format(graph_url),
        headers={'Authorization': 'Bearer {0}'.format(token)},
        params={
            '$select': 'displayName,mail,userPrincipalName'
        })
    return user.json()

def store_user(request, user, result):
    try:
        now = datetime.now()
        set_session_data(request, result['access_token'], result['refresh_token'], int(now.timestamp()) + result['expires_in'])
    except Exception as e:
        print(e)

def _get_auth_app(cache=None):
  auth_app = msal.ConfidentialClientApplication(
    # client_id='1ea518ef-4ac6-41d8-af2e-0adac5b437bf',
    # client_credential='fBB8Q~5WN.t5xkM3ZasLHC-ahesszJaptf6~rbwa',
    client_id='d0c86695-c744-460e-8e92-d79bedc7ee37',
    client_credential='FSc8Q~UIl9~pfSzSfrS0fdaAtJ86i25Fsqvh6bxl',
    authority="https://login.microsoftonline.com/common",
    token_cache=cache
  ) 
  return auth_app

def get_auth_app(request):
  cache = load_cache(request)
  auth_app = _get_auth_app(cache)
  return auth_app
    
def is_authenticated(session_data):
    try:
        now = datetime.now()
        if 'microsoft_access_token_expiration_time' in session_data:
            if session_data['microsoft_access_token_expiration_time'] > int(now.timestamp()):
                return True
            return False
        return False
    except:
        return False
    
def load_cache(request):
  # Check for a token cache in the session
  cache = msal.SerializableTokenCache()
  if request.session.get('token_cache'):
    cache.deserialize(request.session['token_cache'])
  return cache

def save_cache(request, cache):
  # If cache has changed, persist back to session
  if cache.has_state_changed:
    request.session['token_cache'] = cache.serialize()

def get_token_from_code(request):
  cache = load_cache(request)
  auth_app = get_auth_app(request)

  # Get the flow saved in session
  flow = request.session.pop('auth_flow', {})
  result = auth_app.acquire_token_by_auth_code_flow(flow, request.GET)
  save_cache(request, cache)

  return result

def login(request):
    app = _get_auth_app()
    result = app.initiate_auth_code_flow(
        scopes=scopes,
        redirect_uri="http://localhost:8000/swirl/microsoft-callback"
    )
    if result and result['auth_uri']:
        try:
            request.session['auth_flow'] = result
        except Exception as e:
            print(e)
        return HttpResponseRedirect(result['auth_uri'])

def callback(request):
    # Make the token request
    result = get_token_from_code(request)
    user = get_user(result['access_token'])
    store_user(request, user, result)
    return HttpResponseRedirect('/swirl/')