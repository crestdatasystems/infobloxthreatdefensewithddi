# File: infoblox_undo_iq_for_td_recommendation_action.py
#
# Copyright 2026 Infoblox Inc.
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

from urllib.parse import quote

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class UndoIqForTdRecommendationAction(BaseAction):
    """Class to handle undo iq for td recommendation action action.

    This action reverses a previously executed recommendation action (e.g., allow a
    blocked indicator, remove the risky flag from an asset, revert a policy change).
    The audit entry ID is obtained from the 'execute iq for td recommendation action' output;
    the server resolves the recommendation type, target, and action from that ID.
    """

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        This action reverses a single recommendation action, so 'audit_entry_id' must be a
        single ID; comma-separated multiple IDs are not supported (matching the 'execute iq for
        td recommendation action' action, which also rejects comma-separated lists).

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        audit_entry_id = self._param.get("audit_entry_id", "")
        if "," in audit_entry_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MULTIPLE_VALUES_NOT_SUPPORTED.format(key="audit_entry_id"))

        ret_val = self._connector.validator.validate_path_identifier(self._action_result, audit_entry_id, "audit_entry_id")
        if phantom.is_fail(ret_val):
            return ret_val

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Undo IQ for TD Recommendation Action"))

    def __make_api_call(self):
        """
        Make the API call to undo the recommendation action.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        headers = {"Accept": "application/json"}

        endpoint = consts.IQ_FOR_TD_INSIGHT_UNDO_ACTION_ENDPOINT.format(quote(str(self._param.get("audit_entry_id")), safe=""))

        return self._connector.util.make_rest_call(
            endpoint=endpoint,
            action_result=self._action_result,
            method="post",
            headers=headers,
        )

    def __validate_response(self, response):
        """
        Validate the structure of the API response.

        Args:
            response: The API response

        Returns:
            int: phantom.APP_SUCCESS if the response is well-formed, phantom.APP_ERROR otherwise
        """
        if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object with a 'result' object")
        return phantom.APP_SUCCESS

    def __handle_response(self, response):
        """
        Handle the API response and update the action result.

        Args:
            response: The API response

        Returns:
            int: phantom.APP_SUCCESS if the undo succeeded, phantom.APP_ERROR otherwise
        """
        result = response.get("result", {})
        undo_action = result.get("action", "")
        status = result.get("status", "")

        self._action_result.add_data(response)

        audit_entry_id = self._param.get("audit_entry_id")
        summary = {"audit_entry_id": audit_entry_id, "action": undo_action, "status": status}
        self._action_result.update_summary(summary)

        if status != "succeeded":
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.ACTION_UNDO_RECOMMENDATION_ACTION_FAILED.format(audit_entry_id=audit_entry_id)
            )

        message = consts.ACTION_UNDO_RECOMMENDATION_ACTION_SUCCESS_RESPONSE.format(action=undo_action, audit_entry_id=audit_entry_id)
        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute the undo iq for td recommendation action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call
        Step 4: Validate and handle response

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Make API call
        self._connector.save_progress(f"Undoing recommendation action for audit entry ID: {self._param.get('audit_entry_id')}")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Validate and handle response
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        return self.__handle_response(response)
