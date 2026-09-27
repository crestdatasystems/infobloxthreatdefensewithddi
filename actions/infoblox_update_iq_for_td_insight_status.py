# File: infoblox_update_iq_for_td_insight_status.py
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

import json

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class UpdateIqForTdInsightStatus(BaseAction):
    """Class to handle update iq for td insight status action.

    This action updates the workflow status of a specific IQ for TD Insight in Infoblox,
    optionally recording an analyst comment describing the change.
    """

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        status = self._param.get("status")
        if status not in consts.IQ_FOR_TD_INSIGHT_STATUS_VALUES:
            return self._action_result.set_status(
                phantom.APP_ERROR, consts.ERROR_INVALID_SELECTION.format("status", ", ".join(consts.IQ_FOR_TD_INSIGHT_STATUS_VALUES))
            )

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Update IQ for TD Insight Status"))

    def __build_payload(self):
        """
        Build the request payload for the status update.

        Returns:
            dict: Request payload for the API call
        """
        payload = {
            "insight_id": self._param.get("insight_id"),
            "status": self._param.get("status"),
        }

        comment = self._param.get("comment")
        if comment:
            payload["comment"] = comment

        return payload

    def __make_api_call(self, payload):
        """
        Make the API call to update the insight status.

        Args:
            payload (dict): Request payload

        Returns:
            tuple: (status, response) - Status code and API response
        """
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        self._connector.debug_print(f"Updating insight status with payload: {payload}")

        return self._connector.util.make_rest_call(
            endpoint=consts.IQ_FOR_TD_INSIGHT_STATUS_ENDPOINT,
            action_result=self._action_result,
            method="put",
            headers=headers,
            data=payload,
        )

    def __handle_response(self, response):
        """
        Handle the API response and update the action result.

        Args:
            response: The API response

        Returns:
            int: phantom.APP_SUCCESS on successful processing
        """
        insight_id = self._param.get("insight_id")
        status = self._param.get("status")

        # The status endpoint's response body is not part of its documented contract, so publish a
        # stable, typed datapath rather than whatever ad-hoc object the API returns. The raw body is
        # preserved verbatim as a serialized string for troubleshooting.
        self._action_result.add_data(
            {
                "insight_id": insight_id,
                "status": status,
                "response": json.dumps(response) if response else "",
            }
        )

        summary = {"insight_id": insight_id, "status": status}
        self._action_result.update_summary(summary)

        message = consts.ACTION_UPDATE_INSIGHT_STATUS_SUCCESS_RESPONSE.format(status=status, insight_id=insight_id)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute update iq for td insight status action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build request payload
        Step 4: Make API call
        Step 5: Handle response

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

        # Step 3: Build request payload
        payload = self.__build_payload()

        # Step 4: Make API call
        self._connector.save_progress(f"Updating status for insight ID: {self._param.get('insight_id')}")
        ret_val, response = self.__make_api_call(payload)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 6: Return results
        self._connector.save_progress("Insight status updated successfully")
        return phantom.APP_SUCCESS
