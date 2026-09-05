# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.entra.views.app import MicrosoftCallbackEndpoint, MicrosoftOauthInitiateEndpoint
from plane.entra.views.space import (
    MicrosoftCallbackSpaceEndpoint,
    MicrosoftOauthInitiateSpaceEndpoint,
)

urlpatterns = [
    path("microsoft/", MicrosoftOauthInitiateEndpoint.as_view(), name="microsoft-initiate"),
    path("microsoft/callback/", MicrosoftCallbackEndpoint.as_view(), name="microsoft-callback"),
    path(
        "spaces/microsoft/",
        MicrosoftOauthInitiateSpaceEndpoint.as_view(),
        name="space-microsoft-initiate",
    ),
    path(
        "spaces/microsoft/callback/",
        MicrosoftCallbackSpaceEndpoint.as_view(),
        name="space-microsoft-callback",
    ),
]
