"""
@author:     Sid Probstein
@contact:    sid@swirl.today
"""

from django.contrib.auth.models import Group, User
from rest_framework import serializers

from swirl.models import AIProvider, QueryTransform, Result, Search, SearchProvider
from swirl.scope import check_scope


def _validate_provider_scope(serializer, attrs):
    """Run the scope rule over the provider this payload would produce.

    Builds an unsaved SearchProvider from the incoming attributes merged over
    the existing instance (so a PATCH that only flips `active` is judged
    against the stored query_template), then calls the single rule in
    swirl/scope.py.
    """
    instance = serializer.instance
    provider = SearchProvider(
        name=attrs.get('name', getattr(instance, 'name', '')),
        active=attrs.get('active', getattr(instance, 'active', False)),
        query_template=attrs.get(
            'query_template', getattr(instance, 'query_template', '')),
        query_template_json=attrs.get(
            'query_template_json', getattr(instance, 'query_template_json', None)),
        tags=attrs.get('tags', getattr(instance, 'tags', [])),
        config=attrs.get('config', getattr(instance, 'config', {})),
    )
    error = check_scope(provider)
    if error:
        raise serializers.ValidationError({'query_template': error})
    return attrs


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups"]


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]


class SearchProviderSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = SearchProvider
        fields = [
            "id",
            "name",
            "owner",
            "shared",
            "date_created",
            "date_updated",
            "active",
            "default",
            "authenticator",
            "connector",
            "url",
            "query_template",
            "query_template_json",
            "post_query_template",
            "http_request_headers",
            "page_fetch_config_json",
            "query_processors",
            "query_mappings",
            "result_grouping_field",
            "result_processors",
            "response_mappings",
            "result_mappings",
            "results_per_query",
            "credentials",
            "eval_credentials",
            "tags",
            "config",
        ]

    def validate(self, attrs):
        return _validate_provider_scope(self, super().validate(attrs))


class SearchProviderNoCredentialsSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = SearchProvider
        fields = [
            "id",
            "name",
            "owner",
            "shared",
            "date_created",
            "date_updated",
            "active",
            "default",
            "authenticator",
            "connector",
            "url",
            "query_template",
            "query_template_json",
            "post_query_template",
            "http_request_headers",
            "page_fetch_config_json",
            "query_processors",
            "query_mappings",
            "result_processors",
            "response_mappings",
            "result_mappings",
            "results_per_query",
            "tags",
            "config",
        ]

    def validate(self, attrs):
        return _validate_provider_scope(self, super().validate(attrs))


class SearchSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Search
        fields = [
            "id",
            "owner",
            "date_created",
            "date_updated",
            "query_string",
            "query_string_processed",
            "sort",
            "results_requested",
            "searchprovider_list",
            "subscribe",
            "status",
            "pre_query_processors",
            "post_result_processors",
            "result_url",
            "new_result_url",
            "messages",
            "result_mixer",
            "retention",
            "tags",
        ]


class ResultSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = Result
        fields = [
            "id",
            "owner",
            "date_created",
            "date_updated",
            "search_id",
            "searchprovider",
            "query_to_provider",
            "query_processors",
            "result_processors",
            "result_processor_json_feedback",
            "messages",
            "status",
            "retrieved",
            "found",
            "time",
            "json_results",
            "tags",
        ]


class QueryTransformSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = QueryTransform
        fields = [
            "id",
            "name",
            "owner",
            "shared",
            "date_created",
            "date_updated",
            "qrx_type",
            "config_content",
        ]


class QueryTransformNoCredentialsSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = QueryTransform
        fields = [
            "id",
            "name",
            "owner",
            "shared",
            "date_created",
            "date_updated",
            "qrx_type",
            "config_content",
        ]


class DetailSearchRagSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, allow_blank=True)
    additional_content = serializers.DictField(required=False, default=dict)

    class Meta:
        fields = ["message", "additional_content"]


# Minimal Serializers for drf-spectacular OpenAPI documentation only
class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = serializers.CharField()


class StatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


# ---------------------------------------------------------------------------
# AIProvider serializers
# ---------------------------------------------------------------------------

class AIProviderSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = AIProvider
        fields = [
            "id", "name", "owner", "shared", "date_created", "date_updated",
            "active", "api_key", "model", "config", "tags", "defaults", "prompt_overrides",
        ]
        extra_kwargs = {
            "api_key": {"required": False, "allow_blank": True},
        }

    def update(self, instance, validated_data):
        # Preserve api_key when the caller omits it or sends an empty string.
        if validated_data.get("api_key", None) in (None, ""):
            validated_data.pop("api_key", None)
        return super().update(instance, validated_data)


class AIProviderNoCredentialsSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")

    class Meta:
        model = AIProvider
        fields = [
            "id", "name", "owner", "shared", "date_created", "date_updated",
            "active", "model", "config", "tags", "defaults", "prompt_overrides",
        ]
