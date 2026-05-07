from __future__ import annotations

from collections.abc import Mapping, Sequence

from openfeature.flag_evaluation import (
    ErrorCode,
    FlagResolutionDetails,
    Reason,
)
from openfeature.hook import Hook
from openfeature.provider import AbstractProvider, Metadata

from featureflags.hooks import OpenTelemetryFeatureFlagHook
from featureflags.models import FeatureKind
from featureflags.services import (
    get_feature_spec,
    resolve_flag_details,
)


class DjangoAdminFeatureProvider(AbstractProvider):
    def __init__(self) -> None:
        super().__init__()
        self._metadata = Metadata(name="django-admin-feature-provider")
        self._hooks: list[Hook] = [OpenTelemetryFeatureFlagHook()]

    def initialize(self, evaluation_context) -> None:
        self.emit_provider_ready({})

    def get_metadata(self) -> Metadata:
        return self._metadata

    def get_provider_hooks(self) -> list[Hook]:
        return self._hooks

    def resolve_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context=None,
    ) -> FlagResolutionDetails[bool]:
        spec = get_feature_spec(flag_key)
        if spec is None:
            return FlagResolutionDetails(
                value=default_value,
                reason=Reason.DEFAULT,
                error_code=ErrorCode.FLAG_NOT_FOUND,
                error_message=f"Flag {flag_key} not found",
            )

        if spec.kind != FeatureKind.BOOLEAN:
            return FlagResolutionDetails(
                value=default_value,
                reason=Reason.ERROR,
                error_code=ErrorCode.TYPE_MISMATCH,
                error_message=f"Flag {flag_key} is not boolean",
            )

        return resolve_flag_details(
            flag_key,
            spec.kind,
            default_value,
            evaluation_context,
        )

    def resolve_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context=None,
    ) -> FlagResolutionDetails[str]:
        spec = get_feature_spec(flag_key)
        if spec is None:
            return FlagResolutionDetails(
                value=default_value,
                reason=Reason.DEFAULT,
                error_code=ErrorCode.FLAG_NOT_FOUND,
                error_message=f"Flag {flag_key} not found",
            )

        if spec.kind != FeatureKind.VARIANT:
            return FlagResolutionDetails(
                value=default_value,
                reason=Reason.ERROR,
                error_code=ErrorCode.TYPE_MISMATCH,
                error_message=f"Flag {flag_key} is not string/variant",
            )

        return resolve_flag_details(
            flag_key,
            spec.kind,
            default_value,
            evaluation_context,
        )

    def resolve_integer_details(
        self,
        flag_key: str,
        default_value: int,
        evaluation_context=None,
    ) -> FlagResolutionDetails[int]:
        return FlagResolutionDetails(
            value=default_value,
            reason=Reason.DEFAULT,
            error_code=ErrorCode.TYPE_MISMATCH,
            error_message=f"Integer flags are not configured for {flag_key}",
        )

    def resolve_float_details(
        self,
        flag_key: str,
        default_value: float,
        evaluation_context=None,
    ) -> FlagResolutionDetails[float]:
        return FlagResolutionDetails(
            value=default_value,
            reason=Reason.DEFAULT,
            error_code=ErrorCode.TYPE_MISMATCH,
            error_message=f"Float flags are not configured for {flag_key}",
        )

    def resolve_object_details(
        self,
        flag_key: str,
        default_value: Sequence[object] | Mapping[str, object],
        evaluation_context=None,
    ) -> FlagResolutionDetails[Sequence[object] | Mapping[str, object]]:
        return FlagResolutionDetails(
            value=default_value,
            reason=Reason.DEFAULT,
            error_code=ErrorCode.TYPE_MISMATCH,
            error_message=f"Object flags are not configured for {flag_key}",
        )
