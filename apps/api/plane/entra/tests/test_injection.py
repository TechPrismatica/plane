# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.apps import apps


@pytest.mark.unit
def test_entra_app_is_installed():
    assert apps.is_installed("plane.entra")


@pytest.mark.unit
def test_error_codes_are_injected():
    from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES

    assert AUTHENTICATION_ERROR_CODES["MICROSOFT_NOT_CONFIGURED"] == 6900
    assert AUTHENTICATION_ERROR_CODES["MICROSOFT_OAUTH_PROVIDER_ERROR"] == 6901
    assert AUTHENTICATION_ERROR_CODES["MICROSOFT_TENANT_INVALID"] == 6902


@pytest.mark.unit
def test_error_codes_do_not_collide_with_upstream():
    from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES

    codes = list(AUTHENTICATION_ERROR_CODES.values())
    assert len(codes) == len(set(codes)), "duplicate error code values"


@pytest.mark.unit
def test_injection_is_idempotent():
    from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES
    from plane.entra.injection import inject_all

    before = dict(AUTHENTICATION_ERROR_CODES)
    inject_all()
    inject_all()
    assert dict(AUTHENTICATION_ERROR_CODES) == before


@pytest.mark.unit
@pytest.mark.parametrize(
    "name,path",
    [
        ("microsoft-initiate", "/auth/microsoft/"),
        ("microsoft-callback", "/auth/microsoft/callback/"),
        ("space-microsoft-initiate", "/auth/spaces/microsoft/"),
        ("space-microsoft-callback", "/auth/spaces/microsoft/callback/"),
    ],
)
def test_routes_are_injected(name, path):
    from django.urls import resolve, reverse

    assert reverse(name) == path
    assert resolve(path).url_name == name


@pytest.mark.unit
def test_url_injection_does_not_duplicate():
    from plane.authentication import urls as auth_urls
    from plane.entra.injection import inject_urls

    inject_urls()
    inject_urls()
    names = [getattr(p, "name", None) for p in auth_urls.urlpatterns]
    assert names.count("microsoft-initiate") == 1
