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


def inject_all():
    inject_error_codes()
