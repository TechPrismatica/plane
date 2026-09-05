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


@pytest.mark.unit
def test_config_variables_are_injected():
    from plane.utils.instance_config_variables import instance_config_variables

    keys = {v["key"] for v in instance_config_variables}
    assert {
        "IS_MICROSOFT_ENABLED",
        "MICROSOFT_CLIENT_ID",
        "MICROSOFT_CLIENT_SECRET",
        "MICROSOFT_TENANT_ID",
        "ENABLE_MICROSOFT_SYNC",
    } <= keys


@pytest.mark.unit
def test_client_secret_is_marked_encrypted():
    from plane.utils.instance_config_variables import instance_config_variables

    secret = next(v for v in instance_config_variables if v["key"] == "MICROSOFT_CLIENT_SECRET")
    assert secret["is_encrypted"] is True


@pytest.mark.unit
def test_config_injection_does_not_duplicate():
    from plane.entra.injection import inject_config_variables
    from plane.utils.instance_config_variables import instance_config_variables

    inject_config_variables()
    inject_config_variables()
    keys = [v["key"] for v in instance_config_variables]
    assert keys.count("MICROSOFT_CLIENT_ID") == 1


# Collision-vs-idempotency: the guards in injection.py must tell "this
# plugin already placed this" (a no-op, exercised above) apart from "this
# already exists but this plugin did NOT place it" (a collision, which must
# raise). The tests above already prove re-running inject_all()/each
# individual inject_* function is a true no-op. The tests below simulate the
# collision case by forgetting -- via the module's own bookkeeping sets --
# that this plugin placed a given entry, while leaving the entry itself in
# place, exactly as a foreign (e.g. future-upstream) entry would look.


@pytest.mark.unit
def test_error_code_collision_with_foreign_entry_raises():
    from plane.entra import injection

    assert "MICROSOFT_NOT_CONFIGURED" in injection._placed_error_codes
    injection._placed_error_codes.discard("MICROSOFT_NOT_CONFIGURED")
    try:
        with pytest.raises(RuntimeError, match="MICROSOFT_NOT_CONFIGURED"):
            injection.inject_error_codes()
    finally:
        injection._placed_error_codes.add("MICROSOFT_NOT_CONFIGURED")


@pytest.mark.unit
def test_url_collision_with_foreign_entry_raises():
    from plane.entra import injection

    assert "microsoft-initiate" in injection._placed_url_names
    injection._placed_url_names.discard("microsoft-initiate")
    try:
        with pytest.raises(RuntimeError, match="microsoft-initiate"):
            injection.inject_urls()
    finally:
        injection._placed_url_names.add("microsoft-initiate")


@pytest.mark.unit
def test_config_collision_with_foreign_entry_raises():
    from plane.entra import injection

    assert "MICROSOFT_CLIENT_ID" in injection._placed_config_keys
    injection._placed_config_keys.discard("MICROSOFT_CLIENT_ID")
    try:
        with pytest.raises(RuntimeError, match="MICROSOFT_CLIENT_ID"):
            injection.inject_config_variables()
    finally:
        injection._placed_config_keys.add("MICROSOFT_CLIENT_ID")


@pytest.mark.unit
def test_reinjecting_all_after_collision_tests_is_still_a_noop():
    """Sanity check that the collision tests above fully restore state --
    a real double ready() call must remain a true no-op after them."""
    from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES
    from plane.entra.injection import inject_all

    before = dict(AUTHENTICATION_ERROR_CODES)
    inject_all()
    assert dict(AUTHENTICATION_ERROR_CODES) == before
