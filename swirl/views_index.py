'''
Backstage ingest API (TECH_DESIGN_swirl_for_backstage.md section 3.2).

| Method and path                            | Response                        |
|--------------------------------------------|---------------------------------|
| POST   /swirl/index/config/                | 200 effective tuning            |
| POST   /swirl/index/<type>/begin/          | 201 {generation}, 409 if open   |
| POST   /swirl/index/<type>/<gen>/docs/     | 202 {accepted, generation}      |
| POST   /swirl/index/<type>/<gen>/finalize/ | 200 {live, count}, 400 if empty |
| POST   /swirl/index/<type>/<gen>/abort/    | 204                             |
| DELETE /swirl/index/<type>/                | 204                             |
| GET    /swirl/index/                       | 200 list of types               |

Auth is IsAuthenticated plus the swirl.change_searchprovider permission,
satisfied by a Token, a session, HTTP Basic, or a Backstage service principal.
BackstageTokenMiddleware (WP03) verifies the plugin token and sets
request.backstage_principal; BackstagePrincipalAuthentication carries that
decision into DRF, which would otherwise resolve request.user back to
AnonymousUser. A plugin token with no obo maps to the user 'backstage:service',
which holds swirl.change_searchprovider, so the Backstage backend can ingest
without a SWIRL API token of its own.

The filesystem under SWIRL_TANTIVY_DATA_DIR is the source of truth. The
SearchIndexGeneration rows written here are bookkeeping for the admin.
'''

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from swirl.backstage_bearer import BackstagePrincipalAuthentication
from swirl.models import SearchIndexGeneration
from swirl.tantivy_index import generations as gen
from swirl.tantivy_index.manager import MAX_BATCH, default_manager

logger = logging.getLogger(__name__)

INGEST_PERMISSION = 'swirl.change_searchprovider'


def _forbidden():
    return Response(
        {'detail': 'This endpoint requires the {} permission.'.format(
            INGEST_PERMISSION)},
        status=status.HTTP_403_FORBIDDEN)


def _bad_request(message):
    return Response({'detail': str(message)}, status=status.HTTP_400_BAD_REQUEST)


def _not_found(message):
    return Response({'detail': str(message)}, status=status.HTTP_404_NOT_FOUND)


class IndexViewBase(APIView):
    '''Shared auth, permission check and type-name validation.'''

    authentication_classes = [BackstagePrincipalAuthentication,
                              TokenAuthentication, SessionAuthentication,
                              BasicAuthentication]
    permission_classes = [IsAuthenticated]

    @property
    def manager(self):
        return default_manager

    def check_ingest_permission(self, request):
        '''Return a 403 Response when the user may not write the index.'''
        if not request.user.has_perm(INGEST_PERMISSION):
            return _forbidden()
        return None

    def valid_type(self, type_name):
        '''Return (type_name, None) or (None, Response).'''
        try:
            return gen.validate_type_name(type_name), None
        except gen.InvalidTypeName as err:
            return None, _bad_request(err)


########################################


class IndexConfigView(IndexViewBase):
    '''POST /swirl/index/config/ : persist the tuning block.'''

    def get(self, request):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        return Response(self.manager.tuning().to_dict(), status=status.HTTP_200_OK)

    def post(self, request):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        payload = request.data if isinstance(request.data, dict) else None
        if payload is None:
            return _bad_request('the body must be a JSON object')
        try:
            effective = self.manager.configure(payload)
        except ValueError as err:
            return _bad_request(err)
        except OSError as err:
            logger.error('index config: %s', err)
            return _bad_request('could not persist the tuning: {}'.format(err))
        return Response(effective.to_dict(), status=status.HTTP_200_OK)


class IndexListView(IndexViewBase):
    '''GET /swirl/index/ : every type with its live generation, count and size.'''

    def get(self, request):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        return Response({'types': self.manager.all_stats()},
                        status=status.HTTP_200_OK)


class IndexTypeView(IndexViewBase):
    '''DELETE /swirl/index/<type>/ : remove the type and every generation.'''

    def delete(self, request, type_name):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        type_name, bad = self.valid_type(type_name)
        if bad:
            return bad
        deleted = self.manager.delete(type_name)
        if not deleted:
            return _not_found('no index for type "{}"'.format(type_name))
        SearchIndexGeneration.objects.filter(type=type_name).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IndexBeginView(IndexViewBase):
    '''POST /swirl/index/<type>/begin/ : open a generation, 409 if one is open.'''

    def post(self, request, type_name):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        type_name, bad = self.valid_type(type_name)
        if bad:
            return bad
        try:
            generation = self.manager.begin(
                type_name, started_by=getattr(request.user, 'username', ''))
        except gen.GenerationOpen as err:
            return Response(
                {'detail': str(err), 'type': type_name,
                 'generation': err.generation},
                status=status.HTTP_409_CONFLICT)
        except OSError as err:
            logger.error('index begin %s: %s', type_name, err)
            return _bad_request('could not create the generation: {}'.format(err))

        SearchIndexGeneration.objects.update_or_create(
            type=type_name, generation=generation,
            defaults={
                'state': SearchIndexGeneration.STATE_OPEN,
                'doc_count': 0,
                'bytes': 0,
                'finalized_at': None,
                'started_by': request.user if request.user.is_authenticated else None,
            })
        return Response({'type': type_name, 'generation': generation},
                        status=status.HTTP_201_CREATED)


class IndexDocsView(IndexViewBase):
    '''POST /swirl/index/<type>/<gen>/docs/ : add up to MAX_BATCH documents.'''

    def post(self, request, type_name, generation):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        type_name, bad = self.valid_type(type_name)
        if bad:
            return bad
        payload = request.data if isinstance(request.data, dict) else {}
        documents = payload.get('documents')
        if documents is None:
            return _bad_request('the body must carry a "documents" list')
        if not isinstance(documents, list):
            return _bad_request('"documents" must be a list')
        if len(documents) > MAX_BATCH:
            return _bad_request(
                'at most {} documents per request, got {}'.format(
                    MAX_BATCH, len(documents)))
        try:
            accepted = self.manager.add(type_name, generation, documents)
        except gen.GenerationNotFound as err:
            return _not_found(err)
        except gen.InvalidTypeName as err:
            return _bad_request(err)
        except ValueError as err:
            return _bad_request(err)
        except OSError as err:
            logger.error('index docs %s/%s: %s', type_name, generation, err)
            return _bad_request('could not write the batch: {}'.format(err))

        row = SearchIndexGeneration.objects.filter(
            type=type_name, generation=generation).first()
        if row:
            row.doc_count = row.doc_count + accepted
            row.save(update_fields=['doc_count'])
        return Response({'accepted': accepted, 'type': type_name,
                         'generation': generation},
                        status=status.HTTP_202_ACCEPTED)


class IndexFinalizeView(IndexViewBase):
    '''POST /swirl/index/<type>/<gen>/finalize/ : swap LIVE, 400 on zero docs.'''

    def post(self, request, type_name, generation):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        type_name, bad = self.valid_type(type_name)
        if bad:
            return bad
        try:
            result = self.manager.finalize(type_name, generation)
        except gen.NoDocuments as err:
            # The live generation is untouched and this one stays open.
            return _bad_request(err)
        except gen.GenerationNotFound as err:
            return _not_found(err)
        except gen.InvalidTypeName as err:
            return _bad_request(err)
        except OSError as err:
            logger.error('index finalize %s/%s: %s', type_name, generation, err)
            return _bad_request('could not finalize: {}'.format(err))

        SearchIndexGeneration.objects.filter(
            type=type_name, generation=generation).update(
                state=SearchIndexGeneration.STATE_LIVE,
                doc_count=result['count'],
                bytes=result['bytes'],
                finalized_at=timezone.now())
        SearchIndexGeneration.objects.filter(type=type_name).exclude(
            generation=generation).filter(
                state=SearchIndexGeneration.STATE_LIVE).update(
                    state=SearchIndexGeneration.STATE_RETIRED)
        return Response({'type': type_name, 'live': result['live'],
                         'count': result['count'], 'bytes': result['bytes']},
                        status=status.HTTP_200_OK)


class IndexAbortView(IndexViewBase):
    '''POST /swirl/index/<type>/<gen>/abort/ : drop the generation, keep LIVE.'''

    def post(self, request, type_name, generation):
        denied = self.check_ingest_permission(request)
        if denied:
            return denied
        type_name, bad = self.valid_type(type_name)
        if bad:
            return bad
        try:
            self.manager.abort(type_name, generation)
        except gen.GenerationNotFound as err:
            return _not_found(err)
        except gen.InvalidTypeName as err:
            return _bad_request(err)
        except gen.TantivyIndexError as err:
            return _bad_request(err)
        except OSError as err:
            logger.error('index abort %s/%s: %s', type_name, generation, err)
            return _bad_request('could not abort: {}'.format(err))

        SearchIndexGeneration.objects.filter(
            type=type_name, generation=generation).update(
                state=SearchIndexGeneration.STATE_ABORTED,
                finalized_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
