# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import jwt
import pytz
import requests

from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)
from plane.authentication.adapter.oauth import OauthAdapter
from plane.entra.constants import (
    GRAPH_ME_URL,
    GRAPH_PHOTO_METADATA_URL,
    GRAPH_PHOTO_VALUE_URL,
    MICROSOFT_SCOPE,
    MULTI_TENANT_SENTINELS,
)
from plane.license.utils.instance_value import get_configuration_value

GRAPH_SELECT = "id,displayName,givenName,surname,mail,userPrincipalName,mobilePhone"


class MicrosoftOAuthProvider(OauthAdapter):
    userinfo_url = f"{GRAPH_ME_URL}?$select={GRAPH_SELECT}"
    photo_metadata_url = GRAPH_PHOTO_METADATA_URL
    photo_url = GRAPH_PHOTO_VALUE_URL
    scope = MICROSOFT_SCOPE
    provider = "microsoft"

    def authentication_error_code(self):
        return "MICROSOFT_OAUTH_PROVIDER_ERROR"

    def check_sync_enabled(self):
        (enabled,) = get_configuration_value(
            [{"key": "ENABLE_MICROSOFT_SYNC", "default": os.environ.get("ENABLE_MICROSOFT_SYNC", "0")}]
        )
        return enabled == "1"

    def get_avatar_download_headers(self):
        return {"Authorization": f"Bearer {self.token_data.get('access_token')}"}

    def _has_photo(self):
        # Graph 404s the metadata endpoint when the account has no photo (common
        # on work/school accounts). Without this guard base.download_and_upload_avatar()
        # falls back to storing the bearer-gated $value URL as a plain `avatar`
        # string, which the frontend renders as a broken <img>. Probed against
        # /me/photo (metadata) rather than /me/photo/$value, because Graph's
        # binary stream endpoints do not reliably support HEAD.
        try:
            response = requests.get(
                self.photo_metadata_url, headers=self.get_avatar_download_headers(), timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def __init__(self, request, code=None, state=None, callback=None):
        (MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID) = get_configuration_value(
            [
                {"key": "MICROSOFT_CLIENT_ID", "default": os.environ.get("MICROSOFT_CLIENT_ID")},
                {"key": "MICROSOFT_CLIENT_SECRET", "default": os.environ.get("MICROSOFT_CLIENT_SECRET")},
                {"key": "MICROSOFT_TENANT_ID", "default": os.environ.get("MICROSOFT_TENANT_ID")},
            ]
        )

        if not (MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET and MICROSOFT_TENANT_ID):
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MICROSOFT_NOT_CONFIGURED"],
                error_message="MICROSOFT_NOT_CONFIGURED",
            )

        tenant_id = MICROSOFT_TENANT_ID.strip()
        # A tenant-scoped authority is the whole security boundary here. These
        # sentinels silently widen it to every Microsoft tenant in existence.
        if tenant_id.lower() in MULTI_TENANT_SENTINELS:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MICROSOFT_TENANT_INVALID"],
                error_message="MICROSOFT_TENANT_INVALID",
            )
        self.tenant_id = tenant_id

        self.auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        redirect_uri = (
            f"{'https' if request.is_secure() else 'http'}://{request.get_host()}/auth/microsoft/callback/"
        )
        url_params = {
            "client_id": MICROSOFT_CLIENT_ID,
            "scope": self.scope,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        auth_url = f"{self.auth_url}?{urlencode(url_params)}"

        super().__init__(
            request,
            self.provider,
            MICROSOFT_CLIENT_ID,
            self.scope,
            redirect_uri,
            auth_url,
            self.token_url,
            self.userinfo_url,
            MICROSOFT_CLIENT_SECRET,
            code,
            callback=callback,
        )

    def _assert_token_tenant(self, id_token):
        """Reject an id_token minted for a different tenant.

        The signature is not verified: this token arrived over TLS on a direct
        server-to-server call to the tenant's own token endpoint, so the channel
        establishes authenticity (OIDC Core 3.1.3.7 permits skipping signature
        validation exactly in this case). What is checked is the claim the
        channel cannot vouch for -- that the tenant is the configured one.
        """
        if not id_token:
            return
        try:
            claims = jwt.decode(id_token, options={"verify_signature": False})
        except jwt.PyJWTError:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MICROSOFT_OAUTH_PROVIDER_ERROR"],
                error_message="MICROSOFT_OAUTH_PROVIDER_ERROR",
            )
        if claims.get("tid") != self.tenant_id:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MICROSOFT_TENANT_INVALID"],
                error_message="MICROSOFT_TENANT_INVALID",
            )

    def set_token_data(self):
        data = {
            "code": self.code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "scope": self.scope,
        }
        token_response = self.get_user_token(data=data)
        id_token = token_response.get("id_token", "")
        self._assert_token_tenant(id_token)
        super().set_token_data(
            {
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token", None),
                # expires_in is a DURATION in seconds, not an epoch. Upstream's
                # Google provider gets this wrong with datetime.fromtimestamp().
                "access_token_expired_at": (
                    datetime.now(tz=pytz.utc) + timedelta(seconds=token_response.get("expires_in"))
                    if token_response.get("expires_in")
                    else None
                ),
                "refresh_token_expired_at": None,
                "id_token": id_token,
            }
        )

    def set_user_data(self):
        user_info_response = self.get_user_response()
        # `mail` is null under some tenant configurations; UPN is the fallback.
        email = user_info_response.get("mail") or user_info_response.get("userPrincipalName")
        if not email:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["OAUTH_PROVIDER_UNVERIFIED_EMAIL"],
                error_message="OAUTH_PROVIDER_UNVERIFIED_EMAIL",
            )
        display_name = user_info_response.get("displayName") or ""
        name_parts = display_name.split(" ", 1)
        first_name = user_info_response.get("givenName") or (name_parts[0] if name_parts else "")
        last_name = user_info_response.get("surname") or (name_parts[1] if len(name_parts) > 1 else "")
        super().set_user_data(
            {
                "email": email,
                "user": {
                    "avatar": self.photo_url if self._has_photo() else "",
                    "first_name": first_name,
                    "last_name": last_name,
                    "provider_id": user_info_response.get("id"),
                    "is_password_autoset": True,
                },
            }
        )
