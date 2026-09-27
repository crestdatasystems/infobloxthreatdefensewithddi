# File: infoblox_get_iq_for_td_insights_events.py
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

from urllib.parse import quote

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction


class GetIqForTdInsightsEvents(BaseAction):
    """Class to handle retrieving IQ for TD insights events.

    This action retrieves a detailed list of threat-related events for a specific
    Insight ID from Infoblox IQ for TD Insights, supporting multiple filter parameters.
    """

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get IQ for TD Insights Events"))

    def _validate_params(self):
        """
        Validate action parameters for format/content.
        Note: Required parameter validation is handled by SOAR's built-in JSON schema validation.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        ret_val = self._connector.validator.validate_path_identifier(self._action_result, self._param.get("insight_id"), "insight_id")
        if phantom.is_fail(ret_val):
            return ret_val

        # Validate detected_from parameter if provided
        detected_from = self._param.get("detected_from")
        if detected_from:
            if not self._connector.validator.validate_rfc3339_datetime(detected_from):
                return self._action_result.set_status(
                    phantom.APP_ERROR, consts.ERROR_INVALID_RFC3339_DATETIME_FORMAT.format(key="detected_from")
                )

        # Validate detected_to parameter if provided
        detected_to = self._param.get("detected_to")
        if detected_to:
            if not self._connector.validator.validate_rfc3339_datetime(detected_to):
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INVALID_RFC3339_DATETIME_FORMAT.format(key="detected_to"))

        # Validate limit parameter if provided
        limit = self._param.get("limit", consts.IQ_FOR_TD_INSIGHTS_EVENTS_DEFAULT_LIMIT)
        ret_val, self._limit = self._connector.validator.validate_integer(
            self._action_result,
            limit,
            "limit",
            allow_zero=False,
            allow_negative=False,
            max_value=consts.IQ_FOR_TD_INSIGHTS_EVENTS_MAX_LIMIT,
        )
        if phantom.is_fail(ret_val):
            return ret_val

        # Validate device_ip parameter if provided - comma-separated list of IP addresses
        device_ip = self._param.get("device_ip")
        if device_ip:
            for ip in [ip.strip() for ip in device_ip.split(",") if ip.strip()]:
                if not self._connector.validator.validate_ip_address(ip):
                    return self._action_result.set_status(phantom.APP_ERROR, f"Invalid device IP address format: {ip}")

        return phantom.APP_SUCCESS

    def __make_api_call(self):
        """
        Make API call to retrieve IQ for TD insights events.

        Returns:
            tuple: (status, response) - Status code and API response
        """
        insight_id = quote(str(self._param.get("insight_id")), safe="")

        # Build endpoint
        endpoint = consts.IQ_FOR_TD_INSIGHTS_EVENTS_ENDPOINT.format(insight_id)

        # Build query parameters dynamically
        params = {}

        # Note: Exclude threat_level and threat_confidence if set to "All" as API doesn't support it
        threat_level = self._param.get("threat_level")
        if threat_level and threat_level.lower() != "all":
            params["threat_level"] = threat_level

        threat_confidence = self._param.get("threat_confidence")
        if threat_confidence and threat_confidence.lower() != "all":
            params["threat_confidence"] = threat_confidence

        if self._param.get("query"):
            params["query"] = self._param.get("query")
        if self._param.get("tclass"):
            params["tclass"] = self._param.get("tclass")
        if self._param.get("source"):
            params["source"] = self._param.get("source")
        if self._param.get("device_ip"):
            params["device_ip"] = self._param.get("device_ip")
        if self._param.get("device_name"):
            params["device_name"] = self._param.get("device_name")
        if self._param.get("user"):
            params["user"] = self._param.get("user")
        if self._param.get("indicator"):
            params["indicator"] = self._param.get("indicator")
        if self._param.get("detected_from"):
            params["detected_from"] = self._param.get("detected_from")
        if self._param.get("detected_to"):
            params["detected_to"] = self._param.get("detected_to")
        params["limit"] = self._limit

        self._connector.debug_print(f"Making API call to {endpoint}")
        self._connector.debug_print(f"Query parameters: {params}")

        # Make the API call
        ret_val, response = self._connector.util.make_rest_call(endpoint, self._action_result, params=params, method="get")

        if phantom.is_fail(ret_val):
            return ret_val, None

        return phantom.APP_SUCCESS, response

    def __handle_response(self, response):
        """
        Handle the API response and process the insights events data.
        Uses .get() method for safe dictionary access to avoid KeyError exceptions.

        Args:
            response (dict): The API response containing events

        Returns:
            int: phantom.APP_SUCCESS on successful processing, phantom.APP_ERROR otherwise
        """
        # Validate response structure using .get() for safe access
        if not isinstance(response, dict):
            return self._action_result.set_status(phantom.APP_ERROR, "Invalid response format: expected JSON object")

        # Check for events field (actual API response structure)
        events = response.get("events")
        if events is None:
            # Instead of treating it as an error, handle it as a successful request with no results
            self._action_result.add_data({"events": []})  # Add empty events list to data

            # Update summary with zero events
            summary = {
                "total_events": 0,
                "insight_id": self._param.get("insight_id", "Unknown"),
                "limit_applied": self._limit,
            }
            self._action_result.update_summary(summary)

            # Return success with simple informative message
            return self._action_result.set_status(phantom.APP_SUCCESS, "No events found for the specified insight ID")

        self._connector.debug_print("Processing insights events response")

        # Store complete API response
        self._action_result.add_data(response)

        # Count total events
        total_events = len(events) if isinstance(events, list) else 0

        # Generate summary
        summary = {
            "total_events": total_events,
            "insight_id": self._param.get("insight_id", "Unknown"),
            "limit_applied": self._limit,
        }

        self._action_result.update_summary(summary)

        # Set success message using single constant with placeholder
        message = consts.SUCCESS_GET_INSIGHTS_EVENTS.format(total_events)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def execute(self):
        """
        Execute get IQ for TD insights events action following the modular approach.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Make API call
        Step 4: Handle response
        Step 5: Return results

        Returns:
            int: phantom.APP_SUCCESS on successful execution, phantom.APP_ERROR otherwise
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters (format/content only, required validation handled by SOAR)
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Make API call
        insight_id = self._param.get("insight_id")
        self._connector.save_progress(f"Retrieving events for insight ID: {insight_id}")
        ret_val, response = self.__make_api_call()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 4: Handle response
        ret_val = self.__handle_response(response)
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 5: Return results
        self._connector.save_progress("IQ for TD insights events retrieved successfully")
        return phantom.APP_SUCCESS
