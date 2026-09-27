# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from unittest.mock import Mock

import phantom.app as phantom

from infoblox_utils import Validator


def test_path_identifier_rejects_dot_only_values():
    action_result = Mock()
    action_result.set_status.return_value = phantom.APP_ERROR

    for value in (".", "..", " . ", "\t..\n"):
        assert Validator().validate_path_identifier(action_result, value, "insight_id") == phantom.APP_ERROR


def test_path_identifier_allows_opaque_values():
    action_result = Mock()

    for value in ("insight.1", "%2e", "id/with/slash"):
        assert Validator().validate_path_identifier(action_result, value, "insight_id") == phantom.APP_SUCCESS

    action_result.set_status.assert_not_called()


def test_all_reported_path_handlers_apply_identifier_validation():
    root = Path(__file__).resolve().parents[1] / "actions"
    handlers = {
        "infoblox_get_iq_for_td_insights_assets.py": "insight_id",
        "infoblox_get_iq_for_td_insights_indicators.py": "insight_id",
        "infoblox_get_iq_for_td_insights_events.py": "insight_id",
        "infoblox_get_iq_for_td_insight_details.py": "insight_id",
        "infoblox_execute_iq_for_td_recommendation_action.py": "insight_id",
        "infoblox_undo_iq_for_td_recommendation_action.py": "audit_entry_id",
        "infoblox_get_indicator_intel_lookup_result.py": "job_id",
    }

    for filename, parameter in handlers.items():
        source = (root / filename).read_text(encoding="utf-8")
        assert "validate_path_identifier" in source
        assert f'"{parameter}"' in source
