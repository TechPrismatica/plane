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
