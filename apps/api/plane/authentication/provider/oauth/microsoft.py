# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytz
import requests

# Module imports
from plane.authentication.adapter.oauth import OauthAdapter
from plane.license.utils.instance_value import get_configuration_value
from plane.authentication.adapter.error import (
    AUTHENTICATION_ERROR_CODES,
    AuthenticationException,
)


class MicrosoftOAuthProvider(OauthAdapter):
    userinfo_url = "https://graph.microsoft.com/v1.0/me"
    photo_metadata_url = "https://graph.microsoft.com/v1.0/me/photo"
    photo_url = "https://graph.microsoft.com/v1.0/me/photo/$value"
    scope = "openid email profile User.Read"
    provider = "microsoft"

    def get_avatar_download_headers(self):
        return {"Authorization": f"Bearer {self.token_data.get('access_token')}"}

    def _has_photo(self):
        # Graph 404s the metadata endpoint when the account has no photo
        # (common on work/school accounts) — base.download_and_upload_avatar()
        # would otherwise fall back to storing the bearer-token-gated $value
        # URL as a plain `avatar` string, which the frontend renders as a
        # broken <img> without auth. Checked against /me/photo (metadata),
        # not /me/photo/$value (binary stream) — Graph's stream endpoints
        # don't reliably support HEAD, so probing $value directly under-reports.
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
                {
                    "key": "MICROSOFT_CLIENT_ID",
                    "default": os.environ.get("MICROSOFT_CLIENT_ID"),
                },
                {
                    "key": "MICROSOFT_CLIENT_SECRET",
                    "default": os.environ.get("MICROSOFT_CLIENT_SECRET"),
                },
                {
                    "key": "MICROSOFT_TENANT_ID",
                    "default": os.environ.get("MICROSOFT_TENANT_ID"),
                },
            ]
        )

        if not (MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET and MICROSOFT_TENANT_ID):
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["MICROSOFT_NOT_CONFIGURED"],
                error_message="MICROSOFT_NOT_CONFIGURED",
            )

        client_id = MICROSOFT_CLIENT_ID
        client_secret = MICROSOFT_CLIENT_SECRET
        tenant_id = MICROSOFT_TENANT_ID

        self.auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        redirect_uri = f"""{"https" if request.is_secure() else "http"}://{request.get_host()}/auth/microsoft/callback/"""
        url_params = {
            "client_id": client_id,
            "scope": self.scope,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        auth_url = f"{self.auth_url}?{urlencode(url_params)}"

        super().__init__(
            request,
            self.provider,
            client_id,
            self.scope,
            redirect_uri,
            auth_url,
            self.token_url,
            self.userinfo_url,
            client_secret,
            code,
            callback=callback,
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
        super().set_token_data(
            {
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token", None),
                "access_token_expired_at": (
                    datetime.now(tz=pytz.utc) + timedelta(seconds=token_response.get("expires_in"))
                    if token_response.get("expires_in")
                    else None
                ),
                "refresh_token_expired_at": None,
                "id_token": token_response.get("id_token", ""),
            }
        )

    def set_user_data(self):
        user_info_response = self.get_user_response()
        email = user_info_response.get("mail") or user_info_response.get("userPrincipalName")
        if not email:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["OAUTH_PROVIDER_UNVERIFIED_EMAIL"],
                error_message="OAUTH_PROVIDER_UNVERIFIED_EMAIL",
            )
        display_name = user_info_response.get("displayName", "") or ""
        name_parts = display_name.split(" ", 1)
        first_name = user_info_response.get("givenName") or (name_parts[0] if name_parts else "")
        last_name = user_info_response.get("surname") or (name_parts[1] if len(name_parts) > 1 else "")
        user_data = {
            "email": email,
            "user": {
                "avatar": self.photo_url if self._has_photo() else "",
                "first_name": first_name,
                "last_name": last_name,
                "provider_id": user_info_response.get("id"),
                "is_password_autoset": True,
            },
        }
        super().set_user_data(user_data)
