# File: __init__.py
#
# Copyright 2025-2026 Infoblox Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from phantom.action_result import ActionResult


class BaseAction:
    """Base Action class to generate the action objects."""

    def __init__(self, connector, param):
        """Prepare constructor for actions.

        :param connector: Infoblox connector object
        :param param: Parameter dictionary
        """
        self._connector = connector
        self._action_result = connector.add_action_result(ActionResult(dict(param)))
        self._param = param


# Import every action module so its BaseAction subclass registers itself here. The connector's
# handle_action then looks the class up via BaseAction.__subclasses__() instead of importing a
# module built from a runtime string.
from . import (
    infoblox_create_custom_list,
    infoblox_create_network_list,
    infoblox_create_security_policy,
    infoblox_dhcp_lease_lookup,
    infoblox_dns_record_lookup,
    infoblox_execute_iq_for_td_recommendation_action,
    infoblox_get_custom_list,
    infoblox_get_indicator_intel_lookup_result,
    infoblox_get_iq_for_td_insight_details,
    infoblox_get_iq_for_td_insights_assets,
    infoblox_get_iq_for_td_insights_events,
    infoblox_get_iq_for_td_insights_indicators,
    infoblox_get_network_list,
    infoblox_get_security_policy,
    infoblox_host_asset_data_lookup,
    infoblox_indicator_threat_lookup,
    infoblox_initiate_indicator_intel_lookup,
    infoblox_ip_asset_data_lookup,
    infoblox_on_poll,
    infoblox_remove_custom_list,
    infoblox_remove_network_list,
    infoblox_remove_security_policy,
    infoblox_test_connectivity,
    infoblox_undo_iq_for_td_recommendation_action,
    infoblox_update_custom_list,
    infoblox_update_custom_list_items,
    infoblox_update_iq_for_td_insight_status,
    infoblox_update_network_list,
    infoblox_update_security_policy,
)
