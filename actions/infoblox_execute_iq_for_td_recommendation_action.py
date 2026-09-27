# File: infoblox_execute_iq_for_td_recommendation_action.py
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


class ExecuteIqForTdRecommendationAction(BaseAction):
    """Class to handle execute iq for td recommendation action action.

    This action executes a single recommendation action on an IQ for TD Insight. The
    recommendation is referenced by the recommendation ID returned in the
    'key_recommendations' output of the 'get iq for td insight details' action; the server
    resolves the recommendation type, target, and metadata from the stored
    recommendation. A successful call returns an audit entry ID that can be passed
    to the 'undo iq for td recommendation action' action to reverse it.
    """

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        insight_id = self._param.get("insight_id", "")
        if "," in insight_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MULTIPLE_VALUES_NOT_SUPPORTED.format(key="insight_id"))

        ret_val = self._connector.validator.validate_path_identifier(self._action_result, insight_id, "insight_id")
        if phantom.is_fail(ret_val):
            return ret_val

        recommendation_id = self._param.get("recommendation_id", "")
        if "," in recommendation_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MULTIPLE_VALUES_NOT_SUPPORTED.format(key="recommendation_id"))
        self._recommendation_id = recommendation_id.strip()
        if not self._recommendation_id:
            return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_MISSING_REQUIRED_PARAM.format(key="recommendation_id"))

        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Execute IQ for TD Recommendation Action"))

    def __build_payload(self):
        """
        Build the request payload for the execute actions call.

        Returns:
            dict: Request payload for the API call
        """
        item = {"recommendation_id": self._recommendation_id}

        action = self._param.get("action")
        if action:
            item["action"] = action

        return {"items": [item]}

    def __make_api_call(self, payload):
        """
        Make the API call to execute the recommendation action.

        Args:
            payload (dict): Request payload

        Returns:
            tuple: (status, response) - Status code and API response
        """
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        endpoint = consts.IQ_FOR_TD_INSIGHT_EXECUTE_ACTIONS_ENDPOINT.format(quote(str(self._param.get("insight_id")), safe=""))

        self._connector.debug_print(f"Executing recommendation action with payload: {payload}")

        return self._connector.util.make_rest_call(
            endpoint=endpoint,
            action_result=self._action_result,
            method="post",
            headers=headers,
            data=payload,
        )

    def __validate_response(self, response):
        """
        Validate the structure of the API response.

        Args:
            response: The API response

        Returns:
            int: phantom.APP_SUCCESS if the response is well-formed, phantom.APP_ERROR otherwise
        """
        if not isinstance(response, dict) or not isinstance(response.get("results"), list):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object with a 'results' list")
        return phantom.APP_SUCCESS

    def __handle_response(self, response):
        """
        Handle the API response and update the action result.

        Args:
            response: The API response

        Returns:
            int: phantom.APP_SUCCESS if the action succeeded, phantom.APP_ERROR otherwise
        """
        results = response.get("results", [])
        result = results[0] if results else {}
        status = result.get("status", "")

        self._action_result.add_data(response)

        insight_id = self._param.get("insight_id")
        summary = {"insight_id": insight_id, "recommendation_id": self._recommendation_id, "status": status}
        self._action_result.update_summary(summary)

        if status != "succeeded":
            if result:
                details = f"{result.get('reason', 'unknown')}: {result.get('message', '')}".strip(": ")
            else:
                details = "No result returned for the requested recommendation ID"
            message = consts.ACTION_EXECUTE_RECOMMENDATION_ACTION_FAILED.format(insight_id=insight_id, details=details)
            return self._action_result.set_status(phantom.APP_ERROR, message)

        message = consts.ACTION_EXECUTE_RECOMMENDATION_ACTION_SUCCESS.format(insight_id=insight_id)
        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute the execute iq for td recommendation action action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build request payload
        Step 4: Make API call
        Step 5: Validate and handle response

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
        self._connector.save_progress(
            f"Executing recommendation action {self._recommendation_id} for insight ID: {self._param.get('insight_id')}"
        )
        ret_val, response = self.__make_api_call(payload)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Validate and handle response
        ret_val = self.__validate_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        return self.__handle_response(response)
