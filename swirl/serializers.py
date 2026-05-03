"""
@author:     Sid Probstein
@contact:    sid@swirl.today
"""

from django.contrib.auth.models import Group, User
from rest_framework import serializers

from swirl.models import AIProvider, QueryTransform, Result, Search, SearchProvider


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
        ]


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
        ]


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
