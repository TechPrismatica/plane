# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Outside upstream's 5xxx namespace entirely. Their main band runs to 5190,
# but they also use 5900 (RATE_LIMIT_EXCEEDED) and 5999 (AUTHENTICATION_FAILED),
# so "just above the main band" is not safe -- 69xx is.
ENTRA_ERROR_CODES = {
    "MICROSOFT_NOT_CONFIGURED": 6900,
    "MICROSOFT_OAUTH_PROVIDER_ERROR": 6901,
    "MICROSOFT_TENANT_INVALID": 6902,
}

# Entra's multi-tenant authorities. Accepting any of these turns a
# tenant-restricted login into "any Microsoft account on earth", which is the
# GHSA-7j95-vh8g-f365 shape Plane's Google provider guards against.
#
# "9188040d-6c67-4c5b-b112-36a304b66dad" is Microsoft's well-known MSA
# (consumer) tenant GUID -- the GUID form of "consumers". It is a valid
# authority, is not itself one of the word-form sentinels above, and personal
# Microsoft accounts' `tid` claim equals it -- so without listing it here it
# would pass both the sentinel check and the tid check, reopening exactly the
# hole this set exists to close.
MULTI_TENANT_SENTINELS = frozenset(
    {"common", "organizations", "consumers", "9188040d-6c67-4c5b-b112-36a304b66dad"}
)

GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"
GRAPH_PHOTO_METADATA_URL = "https://graph.microsoft.com/v1.0/me/photo"
GRAPH_PHOTO_VALUE_URL = "https://graph.microsoft.com/v1.0/me/photo/$value"

MICROSOFT_SCOPE = "openid email profile User.Read"
