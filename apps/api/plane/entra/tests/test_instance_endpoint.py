# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from unittest.mock import patch
from django.utils import timezone


@pytest.mark.unit
def test_instance_endpoint_is_patched_once():
    from plane.license.api.views.instance import InstanceEndpoint
    from plane.entra.injection import patch_instance_endpoint

    first = InstanceEndpoint.get
    patch_instance_endpoint()
    patch_instance_endpoint()
    assert InstanceEndpoint.get is first, "re-patching must be a no-op"


@pytest.mark.django_db
@pytest.mark.unit
def test_instance_response_carries_microsoft_flag(client):
    from plane.license.models import Instance

    # last_checked_at has no model-level default (see plane/license/models/instance.py);
    # every other test creating an Instance sets it explicitly (see
    # plane/tests/contract/app/test_authentication.py), so this test does too.
    Instance.objects.create(
        instance_name="test",
        is_setup_done=True,
        current_version="1.4.2",
        last_checked_at=timezone.now(),
    )
    with patch("plane.entra.injection.get_configuration_value", return_value=["1"]):
        response = client.get("/api/instances/")
    assert response.status_code == 200
    # InstanceEndpoint.get nests provider flags under "config" (see
    # packages/types/src/instance/base.ts: IInstanceInfo.config.is_microsoft_enabled),
    # not at the top level of the response.
    assert response.data["config"]["is_microsoft_enabled"] is True
