# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Every upstream object this plugin extends, extended in one place.

Django's app registry can call AppConfig.ready() more than once (test
runners, some management commands), so every function here is idempotent.
"""

import os

from plane.entra.constants import ENTRA_ERROR_CODES
from plane.license.utils.instance_value import get_configuration_value

# Track what THIS plugin placed in each shared, mutable collection it
# extends -- as distinct from what was merely already there.
#
# `setdefault`/"skip if present" alone cannot tell true idempotency (this
# plugin's own previous ready() call) apart from a genuine collision (some
# other code got there first). That distinction matters: Plane already ships
# Google, GitHub, GitLab and Gitea, so Microsoft is the obvious next provider
# for upstream to add. If it ever does, upstream's own "microsoft-initiate"
# route / MICROSOFT_* config keys / error codes would silently win a bare
# "skip if present" guard, and this plugin's tenant enforcement would be
# bypassed entirely -- on a green build. These sets let each guard tell the
# two cases apart and raise on the latter.
_placed_error_codes = set()
_placed_config_keys = set()
_placed_url_names = set()


def inject_error_codes():
    from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES

    for name, code in ENTRA_ERROR_CODES.items():
        if name in _placed_error_codes:
            continue
        if name in AUTHENTICATION_ERROR_CODES:
            raise RuntimeError(
                f"plane.entra: error code {name!r} already exists in AUTHENTICATION_ERROR_CODES but was "
                "not placed by plane.entra. Upstream appears to have introduced its own Microsoft "
                "provider -- reconcile plane.entra with it before proceeding."
            )
        AUTHENTICATION_ERROR_CODES[name] = code
        _placed_error_codes.add(name)


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
        name = getattr(pattern, "name", None)
        if name in _placed_url_names:
            continue
        if name in existing:
            raise RuntimeError(
                f"plane.entra: URL name {name!r} already exists in plane.authentication's urlconf but "
                "was not placed by plane.entra. Upstream appears to have introduced its own Microsoft "
                "provider -- reconcile plane.entra with it before proceeding."
            )
        auth_urls.urlpatterns.append(pattern)
        _placed_url_names.add(name)
        existing.add(name)


def inject_config_variables():
    """Extend the aggregated config-variable list in place.

    `instance_config_variables` is computed at import time as
    [*core, *extended]. Mutating the list is visible to every module that
    already imported the name; rebinding it would not be.
    """
    from plane.entra.config import microsoft_config_variables
    from plane.utils.instance_config_variables import instance_config_variables

    existing = {variable["key"] for variable in instance_config_variables}
    for variable in microsoft_config_variables:
        key = variable["key"]
        if key in _placed_config_keys:
            continue
        if key in existing:
            raise RuntimeError(
                f"plane.entra: config key {key!r} already exists in instance_config_variables but was "
                "not placed by plane.entra. Upstream appears to have introduced its own Microsoft "
                "provider -- reconcile plane.entra with it before proceeding."
            )
        instance_config_variables.append(variable)
        _placed_config_keys.add(key)
        existing.add(key)


def patch_instance_endpoint():
    """Add is_microsoft_enabled to /api/instances/.

    The web, space and admin apps decide whether to render a provider's
    sign-in button from this payload, and InstanceEndpoint.get offers no
    extension point. The wrapper runs outside the view's @cache_response, so
    it re-evaluates the flag on a cache hit and never writes to the cache.

    InstanceEndpoint.get nests provider flags under response.data["config"]
    (see packages/types/src/instance/base.ts: IInstanceInfo.config), so that
    is where the flag is added. The early-return path (no Instance row yet)
    returns {"is_activated": False, "is_setup_done": False} with no "config"
    key at all; the guard below leaves that response untouched.
    """
    from plane.license.api.views.instance import InstanceEndpoint

    if getattr(InstanceEndpoint, "_entra_patched", False):
        return

    original_get = InstanceEndpoint.get

    def get(self, request, *args, **kwargs):
        response = original_get(self, request, *args, **kwargs)
        data = getattr(response, "data", None)
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            (is_enabled,) = get_configuration_value(
                [{"key": "IS_MICROSOFT_ENABLED", "default": os.environ.get("IS_MICROSOFT_ENABLED", "0")}]
            )
            data["config"]["is_microsoft_enabled"] = is_enabled == "1"
        return response

    InstanceEndpoint.get = get
    InstanceEndpoint._entra_patched = True


def inject_all():
    inject_error_codes()
    inject_config_variables()
    inject_urls()
    patch_instance_endpoint()
