# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.apps import AppConfig


class EntraConfig(AppConfig):
    name = "plane.entra"
    label = "entra"
    verbose_name = "Microsoft Entra ID authentication"

    def ready(self):
        # Imported here, not at module scope: ready() runs after the app
        # registry is populated, so upstream modules are safe to import.
        from plane.entra.injection import inject_all

        inject_all()
