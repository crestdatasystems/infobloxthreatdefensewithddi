# File: infoblox_get_iq_for_td_insights_assets.py
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


class GetIqForTdInsightsAssets(BaseAction):
    """Class to handle get IQ for TD insights assets action.

    This action retrieves assets associated with a specific Insight ID from Infoblox BloxOne.
    """

    def _validate_params(self):
        """Validate the parameters for the get IQ for TD insights assets action.

        Checks that parameters are of the correct type and format.

        Returns:
            int: phantom.APP_SUCCESS if validation passes, phantom.APP_ERROR otherwise
        """
        self._connector.debug_print("Validating parameters for get IQ for TD insights assets action")

        ret_val = self._connector.validator.validate_path_identifier(self._action_result, self._param.get("insight_id"), "insight_id")
        if phantom.is_fail(ret_val):
            return ret_val

        # Validate ip_address if provided - comma-separated list of IP addresses
        ip_address = self._param.get("ip_address")
        if ip_address:
            for ip in [ip.strip() for ip in ip_address.split(",") if ip.strip()]:
                if not self._connector.validator.validate_ip_address(ip):
                    return self._action_result.set_status(phantom.APP_ERROR, f"Invalid IP address format: {ip}")

        # Validate is_verified if provided
        is_verified = self._param.get("is_verified")
        if is_verified:
            ret_val, is_verified = self._connector.validator.validate_boolean(self._action_result, is_verified, "is_verified")
            if phantom.is_fail(ret_val):
                return ret_val

        # Validate limit if provided (must be a positive integer)
        limit = self._param.get("limit")
        if limit is not None:
            self._connector.debug_print(f"Validating limit parameter: {limit}")
            ret_val, limit = self._connector.validator.validate_integer(
                self._action_result, limit, "limit", allow_zero=False, allow_negative=False
            )
            if phantom.is_fail(ret_val):
                self._connector.debug_print(f"Limit validation failed: {self._action_result.get_message()}")
                return ret_val
        return phantom.APP_SUCCESS

    def __log_action_start(self):
        """Log the start of the action execution."""
        self._connector.save_progress(consts.EXECUTION_START_MSG.format("Get IQ for TD insights assets"))

    def __build_endpoint_and_params(self):
        """Build the endpoint and query parameters for the API call.

        Returns:
            tuple: (endpoint, params)
        """
        insight_id = quote(str(self._param["insight_id"]), safe="")
        endpoint = consts.IQ_FOR_TD_INSIGHTS_ASSETS_ENDPOINT.format(insight_id)
        # Build the query parameters
        params = {}
        if self._param.get("device_name"):
            params["device_name"] = self._param.get("device_name")
        if self._param.get("indicators"):
            params["indicators"] = self._param.get("indicators")
        if self._param.get("users"):
            params["users"] = self._param.get("users")
        if self._param.get("ip_address"):
            params["ip_address"] = self._param.get("ip_address")

        is_verified = self._param.get("is_verified")
        if is_verified:
            params["is_verified"] = str(is_verified).strip().lower() in ("true", "1")

        if self._param.get("limit"):
            params["limit"] = self._param.get("limit")

        self._connector.debug_print(f"Using endpoint: {endpoint} with params: {params}")

        return endpoint, params

    def __make_api_call(self, endpoint, params):
        """Make the API call to retrieve IQ for TD insights assets.

        Args:
            endpoint (str): The API endpoint to call
            params (dict): The query parameters to include

        Returns:
            tuple: (status, response) - Status code and API response
        """
        self._connector.debug_print(f"Making API call to {endpoint} with params {params}")
        return self._connector.util.make_rest_call(endpoint=endpoint, action_result=self._action_result, method="get", params=params)

    def __process_response(self, response):
        """Process the API response and update action result.

        Args:
            response (dict): The API response to process

        Returns:
            int: phantom.APP_SUCCESS on successful processing
        """
        # Asset records carry device names, MAC/IP addresses and user names, so never log the raw
        # response body; the asset count below is enough to diagnose the datapath.
        self._connector.debug_print("Processing insights assets response")

        # Extract assets from the response
        assets = []
        if isinstance(response, dict) and "assets" in response:
            assets = response.get("assets", [])
            self._connector.debug_print(f"Found {len(assets)} assets in the response")
        else:
            self._connector.debug_print("Response does not contain 'assets' key")
            # If for some reason the response format changes, try to handle it gracefully
            if isinstance(response, list):
                assets = response
            else:
                assets = [response] if response else []

        # Add each asset to the action result
        for asset in assets:
            self._action_result.add_data(asset)

        # Create summary
        total_assets = len(assets)
        summary = {
            "total_assets": total_assets,
            "insight_id": self._param.get("insight_id"),
            "limit_applied": self._param.get("limit", consts.IQ_FOR_TD_INSIGHTS_DEFAULT_LIMIT),
        }

        self._connector.debug_print(f"Total assets found: {total_assets}")

        # Set appropriate message based on asset count
        if total_assets == 1:
            message = consts.SUCCESS_GET_INSIGHTS_ASSETS_SINGLE
        else:
            message = consts.SUCCESS_GET_INSIGHTS_ASSETS_MULTIPLE.format(total_assets)

        # Update summary
        self._action_result.update_summary(summary)

        return self._action_result.set_status(phantom.APP_SUCCESS, message)

    def __handle_error(self, ret_val, response):
        """Handle error responses from the API.

        Args:
            ret_val (int): The return value from the API call
            response (dict): The error response from the API

        Returns:
            int: phantom.APP_ERROR with an appropriate error message
        """
        # Check if the error response contains a specific message about the insight not existing
        if isinstance(response, dict) and "error" in response:
            error_message = response.get("error", "")
            if "not found" in str(error_message).lower():
                return self._action_result.set_status(phantom.APP_ERROR, consts.ERROR_INSIGHT_NOT_FOUND)

        # Otherwise, return the status that was already set by the utility
        return self._action_result.get_status()

    def execute(self):
        """Execute get IQ for TD insights assets action.

        Step 1: Log action start
        Step 2: Validate parameters
        Step 3: Build endpoint and parameters
        Step 4: Make API call
        Step 5: Process response or handle errors
        """
        # Step 1: Log action start
        self.__log_action_start()

        # Step 2: Validate parameters
        self._connector.save_progress("Validating parameters")
        ret_val = self._validate_params()
        if phantom.is_fail(ret_val):
            return ret_val

        # Step 3: Build endpoint and parameters
        endpoint, params = self.__build_endpoint_and_params()

        # Step 4: Make API call
        self._connector.save_progress("Retrieving insight assets from Infoblox")
        ret_val, response = self.__make_api_call(endpoint, params)

        # Step 5: Process response or handle errors
        if phantom.is_fail(ret_val):
            return self.__handle_error(ret_val, response)

        return self.__process_response(response)
