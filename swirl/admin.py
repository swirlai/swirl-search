'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import json
import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError, ValidationError
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import AIProvider, SearchProvider, Search, Result, QueryTransform, OauthToken

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AIProvider role vocabulary
# ---------------------------------------------------------------------------

AI_PROVIDER_ROLE_CHOICES = [
    ('chat',      'Chat'),
    ('query',     'Query rewrite'),
    ('rag',       'RAG / summarisation'),
    ('connector', 'GenAI connector'),
    ('reader',    'Reader / page fetcher'),
    ('reranker',  'Reranker'),
]


def _processor_multiple(choices, label=''):
    """Return a MultipleChoiceField rendered as a dual-list FilteredSelectMultiple."""
    return forms.MultipleChoiceField(
        choices=choices,
        required=False,
        label=label,
        widget=FilteredSelectMultiple(label, is_stacked=False),
    )


# ---------------------------------------------------------------------------
# SecretFieldsMixin — masks api_key in admin forms
# ---------------------------------------------------------------------------

class SecretFieldsMixin:
    """
    Replaces secret fields with PasswordInput so values are never echoed back.
    On edit/PATCH, leaving the field blank preserves the existing secret.
    """
    secret_fields: tuple = ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_saveasnew = bool(
            request and getattr(request, 'POST', None) and request.POST.get('_saveasnew')
        )
        for fname in self.secret_fields:
            if fname not in form.base_fields:
                continue
            field = form.base_fields[fname]
            field.widget = forms.PasswordInput(render_value=False)
            has_value = obj and getattr(obj, fname, None)
            if has_value or is_saveasnew:
                field.required = False
                field.help_text = 'Leave blank to keep the current value.'
            else:
                field.help_text = 'Required for a new provider.'
        return form

    def save_model(self, request, obj, form, change):
        for fname in self.secret_fields:
            new_val = form.cleaned_data.get(fname, '')
            if not new_val and change:
                # Preserve the existing value from the database.
                try:
                    original = self.model.objects.get(pk=obj.pk)
                    setattr(obj, fname, getattr(original, fname, ''))
                except self.model.DoesNotExist:
                    pass
        super().save_model(request, obj, form, change)

# ---------------------------------------------------------------------------
# JsonAddMixin — paste-a-JSON-doc creation flow for any ModelAdmin
# ---------------------------------------------------------------------------

class JsonAddMixin:
    """
    Adds a custom changelist URL `<model>/add-json/` that accepts a single
    JSON object or a list of objects and creates the corresponding rows.

    Unknown keys are dropped (with a warning). `owner` may be omitted (the
    current admin user is used) or supplied as a username string.

    Subclasses only need to set `change_list_template` to the partial that
    extends `admin/change_list.html` and renders the extra `object-tools` link.
    The template name returned by `_json_add_template()` is rendered for the
    GET / form-redisplay paths.
    """

    json_add_template = 'admin/swirl/json_add.html'

    def get_urls(self):
        info = (self.model._meta.app_label, self.model._meta.model_name)
        return [
            path(
                'add-json/',
                self.admin_site.admin_view(self.add_via_json_view),
                name='%s_%s_add_json' % info,
            ),
        ] + super().get_urls()

    def _resolve_owner(self, value, fallback):
        if not value:
            return fallback
        if isinstance(value, int):
            User = get_user_model()
            try:
                return User.objects.get(pk=value)
            except User.DoesNotExist:
                return fallback
        if isinstance(value, str):
            User = get_user_model()
            try:
                return User.objects.get(username=value)
            except User.DoesNotExist:
                return fallback
        return fallback

    def _valid_field_names(self):
        return {
            f.name for f in self.model._meta.get_fields()
            if hasattr(f, 'name') and not f.many_to_many and not f.one_to_many
        }

    def _create_from_dict(self, item, request_user):
        if not isinstance(item, dict):
            raise ValidationError(
                'Each entry must be a JSON object; got %s' % type(item).__name__
            )
        item = dict(item)  # don't mutate caller's structure
        item.pop('id', None)  # let the DB assign
        owner = self._resolve_owner(item.pop('owner', None), request_user)
        valid = self._valid_field_names()
        dropped = sorted(k for k in item.keys() if k not in valid)
        filtered = {k: v for k, v in item.items() if k in valid}
        try:
            obj = self.model.objects.create(owner=owner, **filtered)
        except (TypeError, FieldError) as err:
            raise ValidationError(str(err))
        return obj, dropped

    def add_via_json_view(self, request):
        if not self.has_add_permission(request):
            return redirect('..')

        opts = self.model._meta
        context = {
            **self.admin_site.each_context(request),
            'opts': opts,
            'title': 'Add %s via JSON' % opts.verbose_name,
            'app_label': opts.app_label,
            'has_view_permission': True,
        }

        if request.method != 'POST':
            return render(request, self.json_add_template, context)

        raw = (request.POST.get('json_data') or '').strip()
        context['json_data'] = raw
        if not raw:
            messages.error(request, 'Paste a JSON object or array first.')
            return render(request, self.json_add_template, context)
        try:
            data = json.loads(raw)
        except ValueError as err:
            messages.error(request, 'Invalid JSON: %s' % err)
            return render(request, self.json_add_template, context)

        items = data if isinstance(data, list) else [data]
        created, all_dropped = [], set()
        for idx, item in enumerate(items):
            try:
                obj, dropped = self._create_from_dict(item, request.user)
            except ValidationError as err:
                messages.error(
                    request,
                    'Item %d: %s' % (idx, '; '.join(err.messages) if hasattr(err, 'messages') else err),
                )
                return render(request, self.json_add_template, context)
            created.append(obj)
            all_dropped.update(dropped)

        if all_dropped:
            messages.warning(
                request,
                'Ignored unknown field(s): %s' % ', '.join(sorted(all_dropped)),
            )
        messages.success(
            request,
            'Created %d %s%s.' % (
                len(created),
                opts.verbose_name,
                '' if len(created) == 1 else 's',
            ),
        )
        if len(created) == 1:
            return redirect(
                'admin:%s_%s_change' % (opts.app_label, opts.model_name),
                created[0].pk,
            )
        return redirect('admin:%s_%s_changelist' % (opts.app_label, opts.model_name))


##################################################

admin.site.site_header = 'SWIRL'
admin.site.index_title = 'Administration Console'
admin.site.site_title  = 'SWIRL'
# Point "View site" at the SWIRL search UI
admin.site.site_url = '/swirl/'

##################################################

@admin.register(SearchProvider)
class SearchProviderAdmin(JsonAddMixin, admin.ModelAdmin):
    change_list_template = 'admin/swirl/searchprovider/change_list.html'
    save_as = True
    save_on_top = True
    list_display       = ['id', 'name', 'connector', 'active', 'shared', 'default', 'owner']
    list_display_links = ('id', 'name')
    list_editable      = ('active', 'shared', 'default')
    list_filter        = ['active', 'shared', 'connector', 'authenticator']
    search_fields      = ['name', 'url', 'tags']
    ordering           = ['id']
    fieldsets = [
        ('Identity', {
            'fields': ['name', 'owner', 'shared', 'active', 'default', 'tags']
        }),
        ('Connector', {
            'fields': [
                'connector', 'url', 'query_template',
                'query_template_json', 'post_query_template',
                'query_mappings', 'credentials', 'eval_credentials',
                'http_request_headers',
            ]
        }),
        ('Processing', {
            'fields': [
                'query_processors', 'result_processors',
                'result_mappings', 'response_mappings',
                'results_per_query', 'result_grouping_field',
                'page_fetch_config_json',
            ]
        }),
        ('Auth', {
            'fields': ['authenticator']
        }),
    ]

##################################################

@admin.register(Search)
class SearchAdmin(admin.ModelAdmin):
    list_display   = ['id', 'owner', 'query_string', 'status', 'time', 'date_created']
    list_filter    = ['status', 'sort', 'result_mixer']
    search_fields  = ['query_string']
    ordering       = ['-date_created']
    readonly_fields = [
        'id', 'owner', 'date_created', 'date_updated',
        'query_string', 'query_string_processed',
        'sort', 'results_requested', 'searchprovider_list',
        'subscribe', 'status', 'time',
        'pre_query_processors', 'post_result_processors',
        'result_url', 'new_result_url', 'messages',
        'result_mixer', 'retention', 'tags',
    ]

##################################################

@admin.register(QueryTransform)
class QueryTransformAdmin(admin.ModelAdmin):
    list_display  = ['id', 'name', 'qrx_type', 'owner', 'shared']
    list_filter   = ['qrx_type', 'shared']
    search_fields = ['name', 'query_string', 'value']
    ordering      = ['id']

##################################################

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display  = ['id', 'search_id', 'searchprovider', 'status', 'retrieved', 'found', 'date_created']
    list_filter   = ['status', 'searchprovider']
    ordering      = ['-date_created']
    readonly_fields = [
        'id', 'owner', 'date_created', 'date_updated',
        'search_id', 'provider_id', 'searchprovider',
        'query_string_to_provider', 'result_processor_json_feedback',
        'query_to_provider', 'query_processors', 'result_processors',
        'messages', 'status', 'retrieved', 'found', 'time',
        'json_results', 'tags',
    ]

##################################################

@admin.register(OauthToken)
class OauthTokenAdmin(admin.ModelAdmin):
    list_display  = ['id', 'owner', 'idp', 'has_refresh_token']
    list_filter   = ['idp']
    readonly_fields = ['id', 'owner', 'idp']

    @admin.display(boolean=True, description='Refresh token set')
    def has_refresh_token(self, obj):
        return bool(obj.refresh_token)


##################################################
# Pure-Python SVG chart helpers (zero JS, zero extra dependencies)
##################################################

def _searches_by_day_svg(days=30, width=720, height=140, bar_gap=3):
    """Bar chart of daily search volume for the last ``days`` days."""
    from datetime import timedelta
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    from django.utils import timezone
    from django.utils.html import escape
    try:
        since = timezone.now() - timedelta(days=days - 1)
        rows = (
            Search.objects
            .filter(date_created__gte=since)
            .annotate(d=TruncDate('date_created'))
            .values('d').annotate(n=Count('id'))
            .order_by('d')
        )
        by_day = {r['d']: r['n'] for r in rows}
    except Exception:
        return ''

    today = timezone.localdate()
    series = [(today - timedelta(days=days - 1 - i),
               by_day.get(today - timedelta(days=days - 1 - i), 0))
              for i in range(days)]
    total = sum(n for _, n in series)
    peak = max((n for _, n in series), default=0) or 1

    left_pad, right_pad, top_pad, bottom_pad = 32, 8, 10, 22
    plot_w = width - left_pad - right_pad
    plot_h = height - top_pad - bottom_pad
    bar_w = max(1.0, (plot_w - bar_gap * (days - 1)) / days)

    bars, x_ticks = [], []
    for i, (d, n) in enumerate(series):
        x = left_pad + i * (bar_w + bar_gap)
        bar_h = (n / peak) * plot_h
        y = top_pad + (plot_h - bar_h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
            f'fill="#0060A8"><title>{escape(d.isoformat())}: {n}</title></rect>'
        )
        if i % 5 == 0 or i == days - 1:
            x_ticks.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{height - 6}" '
                f'text-anchor="middle" font-size="10" fill="currentColor" opacity="0.6">'
                f'{escape(d.strftime("%m/%d"))}</text>'
            )
    y_axis = (
        f'<text x="{left_pad - 6}" y="{top_pad + 10}" text-anchor="end" '
        f'font-size="10" fill="currentColor" opacity="0.6">{peak}</text>'
        f'<text x="{left_pad - 6}" y="{top_pad + plot_h}" text-anchor="end" '
        f'font-size="10" fill="currentColor" opacity="0.6">0</text>'
        f'<line x1="{left_pad}" y1="{top_pad}" x2="{left_pad}" '
        f'y2="{top_pad + plot_h}" stroke="currentColor" opacity="0.2" />'
        f'<line x1="{left_pad}" y1="{top_pad + plot_h}" '
        f'x2="{width - right_pad}" y2="{top_pad + plot_h}" stroke="currentColor" opacity="0.2" />'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Searches per day, last {days} days, total {total}">'
        f'{y_axis}{"".join(bars)}{"".join(x_ticks)}'
        f'</svg>'
    )


def _horizontal_bar_svg(rows, *, width=720, row_height=24, label_pad=200,
                        right_pad=50, bar_color='#0060A8', empty_label='No data.'):
    """
    rows: list of (label, n) tuples sorted descending.
    Returns a horizontal-bar SVG string.
    """
    from django.utils.html import escape
    if not rows:
        return (
            f'<svg viewBox="0 0 {width} 40" width="100%" height="40" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<text x="12" y="24" font-size="13" fill="currentColor" opacity="0.5">'
            f'{escape(empty_label)}</text></svg>'
        )
    height = row_height * len(rows) + 16
    plot_w = width - label_pad - right_pad
    peak = max(n for _, n in rows) or 1
    parts = []
    for i, (label, n) in enumerate(rows):
        y = 8 + i * row_height
        bar_w = (n / peak) * plot_w
        parts.append(
            f'<text x="{label_pad - 8}" y="{y + 16}" text-anchor="end" '
            f'font-size="12" fill="currentColor">{escape(str(label))[:40]}</text>'
            f'<rect x="{label_pad}" y="{y + 4}" width="{bar_w:.1f}" '
            f'height="{row_height - 8}" fill="{bar_color}" rx="2">'
            f'<title>{escape(str(label))}: {n}</title></rect>'
            f'<text x="{label_pad + bar_w + 6:.1f}" y="{y + 16}" '
            f'font-size="12" fill="currentColor" opacity="0.7">{n}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">'
        f'{"".join(parts)}</svg>'
    )


##################################################
# Activity analytics admin view
##################################################

def _admin_activity_view(request):
    """
    Admin page: searches-by-day, top providers, futile queries.
    Protected by admin.site.admin_view() at registration time.
    """
    from datetime import timedelta
    from django.utils import timezone
    from swirl.admin_analytics import searches_by_day, top_providers, futile_searches

    WINDOW_DAYS = 30

    since = timezone.now() - timedelta(days=WINDOW_DAYS)
    until = timezone.now()

    try:
        sbd = searches_by_day(since=since, until=until)
        n_searches = sum(r['count'] for r in sbd)
    except Exception as exc:
        logger.warning('admin activity: searches_by_day failed: %s', exc)
        sbd = []
        n_searches = 0

    try:
        tp = top_providers(since=since, until=until, limit=10)
        n_providers_active = len(tp)
    except Exception as exc:
        logger.warning('admin activity: top_providers failed: %s', exc)
        tp = []
        n_providers_active = 0

    try:
        futile = futile_searches(since=since, until=until, limit=25)
    except Exception as exc:
        logger.warning('admin activity: futile_searches failed: %s', exc)
        futile = []

    # Build SVGs
    searches_svg = _searches_by_day_svg(days=WINDOW_DAYS)
    providers_svg = _horizontal_bar_svg(
        tp,
        empty_label='No SearchProvider hits in the last 30 days.',
    )

    context = {
        **admin.site.each_context(request),
        'title': 'Activity Analytics',
        'window_days': WINDOW_DAYS,
        'overview': {
            'n_searches':        n_searches,
            'n_providers_active': n_providers_active,
            'n_futile':          len(futile),
        },
        'searches_svg':  searches_svg,
        'providers_svg': providers_svg,
        'futile_rows':   futile,
    }
    return render(request, 'admin/activity.html', context)


##################################################
# Log viewer admin view
##################################################

# Files surfaced by the log viewer. Keep this list short and stable — it
# becomes the tab strip in the UI. Each entry is a (label, relative_path)
# pair; the path is resolved against settings.BASE_DIR so the view stays
# portable across local dev (./logs/) and the Docker layout.
_LOG_VIEWER_FILES = (
    ('django',  'logs/django.log'),
    ('celery',  'logs/celery-worker.log'),
)

# Hard cap on what we read off disk per request. Logs grow unbounded between
# rotations, so we tail the last ~1 MiB rather than slurping the whole file.
# That window comfortably covers tens of thousands of lines on a normal day
# without risking a memory spike when something is logging in a tight loop.
_LOG_VIEWER_TAIL_BYTES = 1024 * 1024

# Default number of lines rendered. The user can override via ?lines=N up to
# the hard cap below — keeps the page responsive when a noisy worker fills
# the tail window with short lines.
_LOG_VIEWER_DEFAULT_LINES = 500
_LOG_VIEWER_MAX_LINES = 5000


def _read_log_tail(path, max_lines):
    """Return the last ``max_lines`` lines of ``path`` as a list of strings.

    Reads at most ``_LOG_VIEWER_TAIL_BYTES`` from the end of the file so a
    runaway log can't blow the request's memory budget. Returns an empty
    list when the file is missing or unreadable — callers should treat that
    as a normal "no logs yet" state.
    """
    import os
    try:
        size = os.path.getsize(path)
    except OSError:
        return []

    start = max(0, size - _LOG_VIEWER_TAIL_BYTES)
    try:
        with open(path, 'rb') as fh:
            fh.seek(start)
            chunk = fh.read()
    except OSError:
        return []

    # Decode tolerantly — log files can mix encodings during incidents.
    text = chunk.decode('utf-8', errors='replace')
    # Drop the partial line at the head if the seek landed mid-line.
    if start > 0:
        first_nl = text.find('\n')
        if first_nl >= 0:
            text = text[first_nl + 1:]
    lines = text.splitlines()
    if max_lines and len(lines) > max_lines:
        lines = lines[-max_lines:]
    return lines


def _admin_log_viewer_view(request):
    """
    Admin page: tail of the server-side log files. Read-only — nothing the
    UI does writes back. Bounded by ``_LOG_VIEWER_TAIL_BYTES`` so a 50 GB
    log can't OOM the request thread.
    """
    import os
    from django.conf import settings

    # Which tab is selected? Default to the first entry. Anything not in
    # the whitelist is rejected to avoid path-traversal via the query string.
    requested = request.GET.get('file', _LOG_VIEWER_FILES[0][0])
    labels = {label: rel for label, rel in _LOG_VIEWER_FILES}
    if requested not in labels:
        requested = _LOG_VIEWER_FILES[0][0]

    # How many lines to render. Cap at the hard limit so a stray ?lines=1e9
    # doesn't churn the renderer.
    try:
        n_lines = int(request.GET.get('lines', _LOG_VIEWER_DEFAULT_LINES))
    except (TypeError, ValueError):
        n_lines = _LOG_VIEWER_DEFAULT_LINES
    n_lines = max(50, min(n_lines, _LOG_VIEWER_MAX_LINES))

    abs_path = os.path.join(settings.BASE_DIR, labels[requested])
    lines = _read_log_tail(abs_path, n_lines)
    try:
        size_bytes = os.path.getsize(abs_path)
    except OSError:
        size_bytes = None

    context = {
        **admin.site.each_context(request),
        'title': 'Log Viewer',
        'log_files': [
            {'label': label, 'rel': rel, 'selected': label == requested}
            for label, rel in _LOG_VIEWER_FILES
        ],
        'selected_label': requested,
        'selected_rel':   labels[requested],
        'lines':          lines,
        'line_count':     len(lines),
        'size_bytes':     size_bytes,
        'tail_bytes':     _LOG_VIEWER_TAIL_BYTES,
        'n_lines':        n_lines,
        'max_lines':      _LOG_VIEWER_MAX_LINES,
    }
    return render(request, 'admin/log_viewer.html', context)


##################################################
# Register extra admin URLs (activity page lives at /admin/activity/)
##################################################

def _extend_admin_urls(original_get_urls):
    """Prepend SWIRL-specific paths to admin.site.get_urls()."""
    def wrapper():
        urls = original_get_urls()
        extras = [
            path(
                'activity/',
                admin.site.admin_view(_admin_activity_view),
                name='admin_activity',
            ),
            path(
                'log-viewer/',
                admin.site.admin_view(_admin_log_viewer_view),
                name='admin_log_viewer',
            ),
        ]
        return extras + urls
    return wrapper


admin.site.get_urls = _extend_admin_urls(admin.site.get_urls)


##################################################
# Model grouping: split the swirl app into sub-groups and tag
# all apps with a category so the index template can render
# category banners between cards (mirrors swirl1025im approach).
##################################################

SWIRL_MODEL_GROUPS = [
    ('Configuration', 'swirl_configuration', [
        'AIProvider', 'SearchProvider', 'QueryTransform',
    ]),
    ('Runtime', 'swirl_runtime', [
        'Search', 'Result', 'OauthToken',
    ]),
]

APP_CATEGORIES = {
    'auth':               'Users & Access',
    'authtoken':          'Users & Access',
    'admin':              'Audit',
    'django_celery_beat': 'Scheduling',
    'sessions':           'System',
    'contenttypes':       'System',
}

CATEGORY_ORDER = ['SWIRL', 'Users & Access', 'Audit', 'Scheduling', 'System', 'Other']
_SWIRL_GROUP_ORDER = [label for label, _, __ in SWIRL_MODEL_GROUPS] + ['Other']

_original_get_app_list = admin.site.get_app_list


def _swirl_get_app_list(request, app_label=None):
    app_list = _original_get_app_list(request, app_label)

    swirl_app  = next((a for a in app_list if a.get('app_label') == 'swirl'), None)
    other_apps = [a for a in app_list if a.get('app_label') != 'swirl']

    synthetic = []
    if swirl_app is not None:
        models_by_name = {m.get('object_name'): m for m in swirl_app.get('models', [])}
        accounted = set()
        for display_name, pseudo_label, obj_names in SWIRL_MODEL_GROUPS:
            group_models = [models_by_name[n] for n in obj_names if n in models_by_name]
            if not group_models:
                continue
            accounted.update(obj_names)
            synthetic.append({
                'name':             display_name,
                'app_label':        pseudo_label,
                'app_url':          swirl_app.get('app_url', ''),
                'has_module_perms': swirl_app.get('has_module_perms', True),
                'models':           group_models,
                'category':         'SWIRL',
            })
        leftover = [m for m in swirl_app.get('models', [])
                    if m.get('object_name') not in accounted]
        if leftover:
            synthetic.append({
                'name': 'Other', 'app_label': 'swirl_other',
                'app_url': swirl_app.get('app_url', ''),
                'has_module_perms': swirl_app.get('has_module_perms', True),
                'models': leftover, 'category': 'SWIRL',
            })

    for app in other_apps:
        app['category'] = APP_CATEGORIES.get(app.get('app_label'), 'Other')

    all_apps = synthetic + other_apps

    def sort_key(a):
        cat = a.get('category', 'Other')
        ci = CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else len(CATEGORY_ORDER)
        if cat == 'SWIRL':
            name = a.get('name', '')
            si = _SWIRL_GROUP_ORDER.index(name) if name in _SWIRL_GROUP_ORDER else len(_SWIRL_GROUP_ORDER)
            return (ci, si, name)
        return (ci, 0, a.get('name', '').lower())

    all_apps.sort(key=sort_key)
    return all_apps


admin.site.get_app_list = _swirl_get_app_list


##################################################
# Inject dashboard data into every admin page's template context
##################################################

def _swirl_each_context(request):
    """Wraps Django's each_context to add charts + status strip to the index."""
    ctx = _original_each_context(request)

    try:
        ctx['swirl_query_chart_svg']  = _searches_by_day_svg(days=30)
        ctx['swirl_query_chart_days'] = 30
    except Exception as exc:
        logger.warning('admin: search chart failed: %s', exc)
        ctx['swirl_query_chart_svg'] = ''

    try:
        from swirl.admin_analytics import top_providers
        tp = top_providers(limit=8)
        ctx['swirl_provider_chart_svg']  = _horizontal_bar_svg(
            tp,
            empty_label='No SearchProvider hits in the last 30 days.',
        )
        ctx['swirl_provider_chart_days'] = 30
    except Exception as exc:
        logger.warning('admin: provider chart failed: %s', exc)
        ctx['swirl_provider_chart_svg'] = ''

    try:
        from swirl.banner import SWIRL_VERSION
        from swirl.utils import is_running_celery_redis
        celery_ok = is_running_celery_redis()
        ctx['swirl_status_strip'] = {
            'version':               SWIRL_VERSION,
            'celery':                {'ok': celery_ok, 'detail': 'OK' if celery_ok else 'Not reachable'},
            'search_provider_count': SearchProvider.objects.count(),
            'search_count':          Search.objects.count(),
        }
    except Exception as exc:
        logger.warning('admin: status strip failed: %s', exc)
        ctx['swirl_status_strip'] = None

    return ctx


_original_each_context = admin.site.each_context
admin.site.each_context = _swirl_each_context


# ---------------------------------------------------------------------------
# AIProvider admin
# ---------------------------------------------------------------------------

class AIProviderAdminForm(forms.ModelForm):
    tags = _processor_multiple(AI_PROVIDER_ROLE_CHOICES, label='Active for role (tags)')
    defaults = _processor_multiple(AI_PROVIDER_ROLE_CHOICES, label='Default for role')

    class Meta:
        model = AIProvider
        fields = '__all__'


@admin.register(AIProvider)
class AIProviderAdmin(JsonAddMixin, SecretFieldsMixin, admin.ModelAdmin):
    form = AIProviderAdminForm
    model = AIProvider
    change_list_template = 'admin/swirl/aiprovider/change_list.html'

    secret_fields = ('api_key',)
    save_as = True
    save_on_top = True

    list_display = ('id', 'name', 'model', 'active', 'shared', 'defaults_display', 'owner', 'date_updated')
    list_display_links = ('id', 'name')
    list_editable = ('active', 'shared')
    list_filter = ('active', 'shared')
    search_fields = ('name', 'model')
    readonly_fields = ('date_created', 'date_updated')
    ordering = ('-date_updated',)

    fieldsets = (
        ('Identity', {
            'fields': ('name', ('owner', 'shared'), 'active'),
        }),
        ('Model', {
            'fields': ('model', 'api_key', 'config'),
            'description': (
                'Set <b>model</b> to any LiteLLM-supported model string, e.g. '
                '<code>gpt-4o</code>, <code>anthropic/claude-3-5-sonnet-20241022</code>, '
                '<code>ollama/llama3</code>. '
                'Store the API key here — it never needs to go in <code>.env</code>.'
            ),
        }),
        ('Role tags', {
            'fields': ('tags', 'defaults'),
            'description': (
                '<b>tags</b> — roles this provider is available for. '
                '<b>defaults</b> — roles it is the default for. '
                'Exactly one provider should be default per role '
                '(<b>chat / query / rag / connector</b>).'
            ),
        }),
        ('Audit', {
            'classes': ('collapse',),
            'fields': ('date_created', 'date_updated'),
        }),
    )

    @admin.display(description='Default for')
    def defaults_display(self, obj):
        return ', '.join(obj.defaults or []) or '—'
