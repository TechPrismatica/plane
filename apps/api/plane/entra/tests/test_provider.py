# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from unittest.mock import patch

from plane.authentication.adapter.error import AuthenticationException


def _config(client_id="cid", secret="sec", tenant="11111111-2222-3333-4444-555555555555"):
    return [client_id, secret, tenant]


@pytest.fixture
def rf_request(rf):
    request = rf.get("/auth/microsoft/")
    request.session = {}
    return request


@pytest.mark.unit
@pytest.mark.parametrize("sentinel", ["common", "organizations", "consumers", "COMMON", " common "])
def test_multi_tenant_sentinels_are_rejected(rf_request, sentinel):
    from plane.entra.provider import MicrosoftOAuthProvider

    with patch("plane.entra.provider.get_configuration_value", return_value=_config(tenant=sentinel)):
        with pytest.raises(AuthenticationException) as exc:
            MicrosoftOAuthProvider(request=rf_request, state="s")
    assert exc.value.error_code == 6902


@pytest.mark.unit
def test_missing_tenant_is_rejected(rf_request):
    from plane.entra.provider import MicrosoftOAuthProvider

    with patch("plane.entra.provider.get_configuration_value", return_value=_config(tenant="")):
        with pytest.raises(AuthenticationException) as exc:
            MicrosoftOAuthProvider(request=rf_request, state="s")
    assert exc.value.error_code == 6900


@pytest.mark.unit
def test_auth_url_is_tenant_scoped(rf_request):
    from plane.entra.provider import MicrosoftOAuthProvider

    with patch("plane.entra.provider.get_configuration_value", return_value=_config()):
        provider = MicrosoftOAuthProvider(request=rf_request, state="s")
    url = provider.get_auth_url()
    assert url.startswith(
        "https://login.microsoftonline.com/11111111-2222-3333-4444-555555555555/oauth2/v2.0/authorize?"
    )
    assert "/common/" not in url


@pytest.mark.unit
def test_email_falls_back_to_upn_when_mail_is_null(rf_request):
    from plane.entra.provider import MicrosoftOAuthProvider

    with patch("plane.entra.provider.get_configuration_value", return_value=_config()):
        provider = MicrosoftOAuthProvider(request=rf_request, code="c")
    provider.token_data = {"access_token": "t"}
    graph = {"id": "u1", "mail": None, "userPrincipalName": "u@example.com", "displayName": "Ada Lovelace"}
    with patch.object(MicrosoftOAuthProvider, "get_user_response", return_value=graph), patch.object(
        MicrosoftOAuthProvider, "_has_photo", return_value=False
    ):
        provider.set_user_data()
    assert provider.user_data["email"] == "u@example.com"
    assert provider.user_data["user"]["first_name"] == "Ada"
    assert provider.user_data["user"]["last_name"] == "Lovelace"


@pytest.mark.unit
def test_tid_mismatch_is_rejected(rf_request):
    import jwt

    from plane.entra.provider import MicrosoftOAuthProvider

    with patch("plane.entra.provider.get_configuration_value", return_value=_config()):
        provider = MicrosoftOAuthProvider(request=rf_request, code="c")
    foreign = jwt.encode({"tid": "99999999-9999-9999-9999-999999999999"}, "k", algorithm="HS256")
    token_response = {"access_token": "t", "expires_in": 3600, "id_token": foreign}
    with patch.object(MicrosoftOAuthProvider, "get_user_token", return_value=token_response):
        with pytest.raises(AuthenticationException) as exc:
            provider.set_token_data()
    assert exc.value.error_code == 6902


@pytest.mark.unit
def test_expiry_is_now_plus_duration_not_epoch(rf_request):
    from datetime import datetime, timezone

    import jwt

    from plane.entra.provider import MicrosoftOAuthProvider

    with patch("plane.entra.provider.get_configuration_value", return_value=_config()):
        provider = MicrosoftOAuthProvider(request=rf_request, code="c")
    good = jwt.encode({"tid": "11111111-2222-3333-4444-555555555555"}, "k", algorithm="HS256")
    token_response = {"access_token": "t", "expires_in": 3600, "id_token": good}
    with patch.object(MicrosoftOAuthProvider, "get_user_token", return_value=token_response):
        provider.set_token_data()
    expiry = provider.token_data["access_token_expired_at"]
    assert expiry.year == datetime.now(tz=timezone.utc).year
