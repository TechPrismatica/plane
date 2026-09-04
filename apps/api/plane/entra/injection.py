# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Every upstream object this plugin extends, extended in one place.

Django's app registry can call AppConfig.ready() more than once (test
runners, some management commands), so every function here is idempotent.
"""

from plane.entra.constants import ENTRA_ERROR_CODES


def inject_error_codes():
    from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES

    for name, code in ENTRA_ERROR_CODES.items():
        AUTHENTICATION_ERROR_CODES.setdefault(name, code)


def inject_urls():
    """Append this plugin's routes to plane.authentication's urlconf.

    Safe from ready(): Django resolves ROOT_URLCONF lazily on the first
    request, which is strictly after every AppConfig.ready() has run. The
    list is mutated in place so the `include()` already registered against
    the module sees the additions.
    """
    from plane.authentication import urls as auth_urls
    from plane.entra.urls import urlpatterns as entra_urlpatterns

    existing = {getattr(pattern, "name", None) for pattern in auth_urls.urlpatterns}
    for pattern in entra_urlpatterns:
        if getattr(pattern, "name", None) not in existing:
            auth_urls.urlpatterns.append(pattern)


def inject_all():
    inject_error_codes()
    inject_urls()
