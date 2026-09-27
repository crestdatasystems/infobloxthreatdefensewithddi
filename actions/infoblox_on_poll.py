# File: infoblox_on_poll.py
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

import time

import phantom.app as phantom

import infoblox_consts as consts
from actions import BaseAction
from infoblox_polling import next_poll_start, parse_event_timestamp


class OnPoll(BaseAction):
    """Class to handle on poll action for DNS Security Events."""

    def execute(self, param=None):
        """Execute the on_poll action.

        Step 1: Check ingestion type from configuration
        Step 2: If DNS Security Events, process those events
        Step 3: If IQ for TD Insights, process those events
        Step 4: Save checkpoint for future polling

        Args:
            param (dict): Parameters provided by Splunk SOAR
                - container_id (str, optional): ID of the container to ingest artifacts into
                - container_count (int, optional): Maximum number of containers to create
                - artifact_count (int, optional): Maximum number of artifacts to create per container
                - start_time (str, optional): Start time for polling
                - end_time (str, optional): End time for polling
        """
        self._connector.save_progress(consts.INFOBLOX_ON_POLL_START_MSG)
        self._connector.debug_print("In action handler for on_poll")

        # Process the standard parameters that may be provided by SOAR
        if param is None:
            param = {}

        config = self._connector.get_config()
        self._is_poll_now = self._connector.is_poll_now()
        self._state = self._connector._state

        # Honor SOAR's container_count/artifact_count only for a manual "Poll Now" run. The IQ
        # insights API returns every matching insight in a single unpaginated response and this
        # poll keeps no checkpoint, so capping a scheduled run would re-process the same first N
        # insights on every run and permanently skip the rest. Scheduled runs are bounded by the
        # asset's IQ for TD filters instead.
        if self._is_poll_now:
            self._container_count = self._normalize_poll_limit(param.get(phantom.APP_JSON_CONTAINER_COUNT))
            self._artifact_count = self._normalize_poll_limit(param.get(phantom.APP_JSON_ARTIFACT_COUNT))
        else:
            self._container_count = None
            self._artifact_count = None

        # Get the ingestion type from the configuration
        ingestion_type = config.get("ingestion_type", "DNS Security Events")

        if ingestion_type == "DNS Security Events":
            self._connector.debug_print("This asset is configured to ingest DNS Security Events")
            # Process parameters for DNS Security Events polling
            ret_val = self._process_parameters(config)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Start the polling process for DNS Security Events
            ret_val, _ = self._poll_dns_security_events()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()
        elif ingestion_type == "IQ for TD Insights":
            self._connector.debug_print("This asset is configured to ingest IQ for TD Insights")
            self._connector.save_progress(consts.INFOBLOX_IQ_FOR_TD_INSIGHTS_POLL_START)

            # Process parameters for IQ for TD Insights polling
            ret_val = self._process_iq_for_td_insights_parameters(config)
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            # Start the polling process for IQ for TD Insights
            ret_val, _ = self._poll_iq_for_td_insights()
            if phantom.is_fail(ret_val):
                return self._action_result.get_status()

            self._connector.save_progress(consts.INFOBLOX_IQ_FOR_TD_INSIGHTS_POLL_FINISH)
        else:
            self._connector.save_progress(f"Invalid ingestion type: {ingestion_type}")
            return self._action_result.set_status(phantom.APP_ERROR, f"Invalid ingestion type: {ingestion_type}")

        return self._action_result.set_status(phantom.APP_SUCCESS)

    @staticmethod
    def _normalize_poll_limit(value):
        """Coerce a SOAR poll limit to a non-negative int, or None when it is absent/unusable.

        Args:
            value: Raw ``container_count``/``artifact_count`` value from the poll parameters

        Returns:
            int or None: The limit to enforce, or None for "no limit"
        """
        if value is None:
            return None
        try:
            limit = int(value)
        except (ValueError, TypeError):
            return None
        return limit if limit >= 0 else None

    def _process_parameters(self, config):
        """Process and validate parameters from the asset configuration.

        Args:
            config (dict): Asset configuration dictionary

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        self._connector.debug_print("Processing parameters for DNS Security Events polling")

        # Initialize parameters from config, mapping user-friendly names to API parameter names
        # Only using the specified parameters

        # Filter parameters
        self._qname = config.get("queried_name", "")  # Query name
        self._policy_name = config.get("policy_name", "")  # Policy name
        self._threat_level = config.get("threat_level", "")  # Threat severity level
        self._threat_class = config.get("threat_class", "")  # Threat category
        self._threat_family = config.get("threat_family", "")  # Threat family
        self._threat_indicator = config.get("threat_indicator", "")  # Threat indicator
        self._policy_action = config.get("policy_action", "")  # Action performed
        self._feed_name = config.get("feed_name", "")  # Threat feed name
        self._network = config.get("network", "")  # Network name/endpoint
        self._limit = config.get("limit", 100)  # Number of results to return

        # Convert comma-separated strings to lists for parameters that accept multiple values
        multi_value_params = [
            "_qname",
            "_policy_name",
            "_threat_class",
            "_threat_family",
            "_threat_indicator",
            "_policy_action",
            "_feed_name",
            "_network",
        ]

        for param_name in multi_value_params:
            param_value = getattr(self, param_name)
            if param_value and isinstance(param_value, str):
                setattr(
                    self,
                    param_name,
                    [x.strip() for x in param_value.split(",") if x.strip()],
                )

        # Convert limit to integer
        try:
            self._limit = int(self._limit)
            if self._limit <= 0:
                self._limit = consts.DEFAULT_LIMIT
        except (ValueError, TypeError):
            self._limit = consts.DEFAULT_LIMIT

        return phantom.APP_SUCCESS

    def _poll_dns_security_events(self):
        """Poll for DNS Security Events from Infoblox.

        Constructs the API request, handles pagination, and processes the response.

        Returns:
            tuple: (phantom.APP_SUCCESS/APP_ERROR, API response data)
        """
        self._connector.save_progress("Polling for DNS Security Events")

        # Get the time range for polling
        t0, t1 = self._get_time_range()
        self._connector.debug_print(f"Polling time range: t0={t0}, t1={t1}")

        # Construct query parameters
        params = self._build_query_params(t0, t1)

        # Make the API request
        endpoint = consts.DNS_SECURITY_EVENTS_ENDPOINT
        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint,
            action_result=self._action_result,
            method="get",
            params=params,
        )

        if phantom.is_fail(ret_val):
            self._connector.save_progress("Failed to fetch DNS security events")
            return ret_val, None

        events = response.get("result", []) if isinstance(response, dict) else []
        if len(events) >= self._limit:
            self._connector.save_progress(
                f"Warning: DNS security event response reached the configured limit of {self._limit}; additional events may remain"
            )

        # Process the response and create containers/artifacts
        ret_val = self._process_dns_security_events(response)
        if phantom.is_fail(ret_val):
            return ret_val, None

        return phantom.APP_SUCCESS, response

    def _get_time_range(self):
        """Determine the time range for polling based on configuration and state.

        For scheduled polling, uses the last event timestamp from state.
        For manual polling, uses a configured lookback period.
        For specific time ranges, uses the provided start_time and end_time parameters.

        Returns:
            tuple: (t0, t1) timestamps in seconds since epoch
        """
        # time.time() is an absolute UTC epoch. datetime.utcnow().timestamp() must not be used
        # here: utcnow() is naive, so .timestamp() re-interprets it as local time and shifts the
        # whole polling window by the host's UTC offset, while the checkpoint stored in state is a
        # true UTC epoch produced by parse_event_timestamp().
        current_time = int(time.time())

        if self._is_poll_now:
            # For manual polling, use the configured lookback period
            max_hours = self._connector.get_config().get("max_hours_backwards", 24)
            try:
                max_hours = int(max_hours)
                if max_hours <= 0:
                    max_hours = 24
            except (ValueError, TypeError):
                max_hours = 24

            t0 = current_time - (max_hours * 3600)
            t1 = current_time

        else:
            # For scheduled polling, use the last event time from state
            self._state = self._connector._state
            last_event_time = self._state.get("last_event_time", None)

            if not last_event_time:
                # If no previous state, use default lookback period
                max_hours = self._connector.get_config().get("max_hours_backwards", 24)
                try:
                    max_hours = int(max_hours)
                    if max_hours <= 0:
                        max_hours = 24
                except (ValueError, TypeError):
                    max_hours = 24

                t0 = current_time - (max_hours * 3600)
            else:
                # Re-fetch the last successful second. Container and artifact source
                # identifiers deduplicate already-saved events, while this inclusive
                # cursor preserves failed events later in the same second.
                t0 = next_poll_start(last_event_time)

            t1 = current_time

        return t0, t1

    def _build_query_params(self, t0, t1):
        """Build query parameters for the DNS security events API.

        Args:
            t0 (int): Start timestamp
            t1 (int): End timestamp

        Returns:
            dict: Query parameters dictionary
        """
        # Required parameters
        params = {
            "t0": t0,
            "t1": t1,
            "_limit": self._limit,  # Use underscore prefix as required by API
        }

        # Add filter parameters if provided - only using the specified parameters
        if self._qname:
            params["qname"] = ",".join(self._qname) if isinstance(self._qname, list) else self._qname

        if self._policy_name:
            params["policy_name"] = ",".join(self._policy_name) if isinstance(self._policy_name, list) else self._policy_name

        if self._threat_level and self._threat_level != "ALL":
            params["threat_level"] = self._threat_level
            # If 'ALL' is selected, don't add the parameter so the API returns all severity levels

        if self._threat_class:
            params["threat_class"] = ",".join(self._threat_class) if isinstance(self._threat_class, list) else self._threat_class

        if self._threat_family:
            params["threat_family"] = ",".join(self._threat_family) if isinstance(self._threat_family, list) else self._threat_family

        if self._threat_indicator:
            params["threat_indicator"] = ",".join(self._threat_indicator) if isinstance(self._threat_indicator, list) else self._threat_indicator

        if self._policy_action:
            params["policy_action"] = ",".join(self._policy_action) if isinstance(self._policy_action, list) else self._policy_action

        if self._feed_name:
            params["feed_name"] = ",".join(self._feed_name) if isinstance(self._feed_name, list) else self._feed_name

        if self._network:
            params["network"] = ",".join(self._network) if isinstance(self._network, list) else self._network

        return params

    def _process_dns_security_events(self, response):
        """Process the DNS security events response and create containers and artifacts.

        Args:
            response (dict): API response containing DNS security events

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        if not response or "result" not in response:
            self._connector.save_progress("No DNS security events found in the response")
            return phantom.APP_SUCCESS

        events = response.get("result", [])
        if not events:
            self._connector.save_progress("No DNS security events found")
            return phantom.APP_SUCCESS

        self._connector.save_progress(f"Processing {len(events)} DNS security events")

        # Sort events by event_time to ensure proper checkpointing
        events.sort(key=lambda x: x.get("event_time", ""))

        failed_events = 0

        # Process each event and stop at the first failure so the checkpoint
        # remains immediately before the event that must be retried.
        for event in events:
            try:
                # Create a container for this event
                container_id = self._create_container_for_event(event)
                if not container_id:
                    failed_events += 1
                    break

                # Create an artifact for this event
                artifact_id = self._create_artifact_for_event(event, container_id)
                if not artifact_id:
                    failed_events += 1
                    break

                # Update the last event time for checkpointing
                event_time_str = event.get("event_time", "")
                if event_time_str:
                    try:
                        event_timestamp = parse_event_timestamp(event_time_str)

                        # Update state with the latest timestamp
                        if not self._is_poll_now:
                            self._state["last_event_time"] = event_timestamp
                            self._connector._state = self._state
                            self._connector.save_state(self._state)
                    except Exception as e:
                        self._connector.debug_print(f"Error parsing event time: {e!s}")
                        failed_events += 1
                        break

            except Exception as e:
                self._connector.debug_print(f"Error processing event: {e!s}")
                failed_events += 1
                break

        if failed_events:
            message = "Failed to ingest a DNS security event; checkpoint preserved for retry"
            self._connector.save_progress(message)
            return self._action_result.set_status(phantom.APP_ERROR, message)

        self._connector.save_progress("Completed processing DNS security events")
        return phantom.APP_SUCCESS

    def _create_container_for_event(self, event):
        """Create a container for a DNS security event.

        Args:
            event (dict): DNS security event data

        Returns:
            int: Container ID if successful, None otherwise
        """

        # Generate a container name from the event data
        qname = event.get("qname", "")
        tclass = event.get("tclass", "")  # Threat class from API response
        severity = event.get("severity", "")  # Severity level

        # Apply the new naming convention
        container_name = f"{tclass} - {qname}" if tclass and qname else "Infoblox DNS Security Event"

        # Map severity to container severity using the constant from infoblox_consts
        container_severity = consts.SEVERITY_MAPPING.get(severity, "high")

        event_time = event.get("event_time", "Unknown Time")
        qname = event.get("qname", "Unknown Domain")
        threat_level = event.get("severity", "Unknown")

        container_name = f"Infoblox DNS Security Event - {qname} - {event_time}"

        # Map severity to container severity
        container_severity = consts.SEVERITY_MAPPING.get(threat_level, "high")

        # Generate a unique source data identifier
        source_data_id = f"{qname}_{event.get('device', '')}_{event.get('event_time', '')}"

        # Create the container JSON
        container_json = {
            "name": container_name,
            "description": f"DNS Security Event for Query {qname}",
            "source_data_identifier": source_data_id,
            "severity": container_severity,
            "label": self._connector.get_config()
            .get("ingest", {})
            .get("container_label"),  # Changed from 'security_event' to 'event' which is more standard
            "data": event,
        }

        # Save container and handle return values properly
        save_result = self._connector.save_container(container_json)

        if save_result and len(save_result) == 3:
            ret_val, message, container_id = save_result
            if phantom.is_success(ret_val):
                if message == "Duplicate container found":
                    self._connector.debug_print(f"Using existing container with ID: {container_id}")
                else:
                    self._connector.debug_print(f"Successfully created container with ID: {container_id}")
                return container_id
            else:
                self._connector.debug_print(f"Failed to create container: {message}")
        else:
            self._connector.debug_print("Unexpected return value from save_container")

        return None

    def _create_artifact_for_event(self, event, container_id):
        """Create an artifact for a DNS security event.

        Args:
            event (dict): DNS security event data
            container_id (int): The container ID to add the artifact to

        Returns:
            int: Artifact ID if successful, None otherwise
        """
        # Get key fields for the artifact
        qname = event.get("qname", "")
        qip = event.get("qip", "")

        # Determine the artifact type based on event data
        if qname:
            artifact_type = "DNS Name"
            artifact_cef_types = {"domainName": ["dns_domain"]}
        elif qip:
            artifact_type = "IP Address"
            artifact_cef_types = {"deviceAddress": ["ip"]}
        else:
            artifact_type = "DNS Security Event"
            artifact_cef_types = {}

        # Build CEF data with only non-empty fields
        # First create a dictionary with all possible fields
        temp_cef_data = {
            # Basic DNS Query Information
            "Query Name": qname,
            "Client IP": qip,
            "Device IP": event.get("device", ""),
            "Source": "Infoblox DNS Security",
            # DNS Query Details
            "Query Type": event.get("qtype", ""),
            "Response Code": event.get("rcode", ""),
            "Response Data": event.get("rdata", ""),
            # Threat Intelligence
            "Threat Class": event.get("tclass", ""),
            "Threat Family": event.get("tfamily", ""),
            "Threat Property": event.get("tproperty", ""),
            "Confidence": event.get("confidence", ""),
            "Threat Indicator": event.get("threat_indicator", ""),
            # Policy Information
            "Policy Action": event.get("policy_action", ""),
            "Policy Name": event.get("policy_name", ""),
            "Feed Type": event.get("feed_type", ""),
            "Feed Name": event.get("feed_name", ""),
            # Network Information
            "Network": event.get("network", ""),
            "User": event.get("user", ""),
            "User Groups": event.get("user_groups", ""),
            "Country": event.get("country", ""),
            "Private IP": event.get("private_ip", ""),
            "MAC Address": event.get("mac_address", ""),
            # Application Information
            "Application Name": event.get("app_name", ""),
            "Application Category": event.get("app_category", ""),
            "DNS View": event.get("dns_view", ""),
            "Endpoint Groups": event.get("endpoint_groups", ""),
            # Temporal Information
            "Event Time": event.get("event_time", ""),
            "Severity": event.get("severity", ""),
        }

        # Filter out empty fields
        cef_data = {response_key: response_value for response_key, response_value in temp_cef_data.items() if response_value}

        # Generate source data identifier for the artifact
        source_data_id = f"{qname}_{qip}_{event.get('event_time', '')}"

        # Create the artifact JSON
        artifact_json = {
            "name": (
                f"{event.get('tclass', '')} - {qname}" if event.get("tclass", "") and qname else "Infoblox DNS Security Event"
            ),  # New naming convention using actual field name from API
            "container_id": container_id,
            "source_data_identifier": source_data_id,
            "cef": cef_data,
            "cef_types": artifact_cef_types,
            "severity": consts.SEVERITY_MAPPING.get(event.get("severity", ""), "high"),
            "data": event,
            "run_automation": True,
            "type": artifact_type,
        }

        # Use save_artifacts instead of save_artifact for better handling
        artifacts_list = [artifact_json]
        save_result = self._connector.save_artifacts(artifacts_list)

        if save_result and len(save_result) == 3:
            ret_val, message, ids = save_result
            if phantom.is_success(ret_val) and ids and len(ids) > 0:
                self._connector.debug_print(f"Successfully saved artifact with ID: {ids[0]}")
                return ids[0]
            else:
                self._connector.debug_print(f"Failed to save artifact: {message}")
        else:
            self._connector.debug_print("Unexpected return value from save_artifacts")

        return None

    def _process_iq_for_td_insights_parameters(self, config):
        """Process and validate parameters from the asset configuration for IQ for TD Insights polling.

        Args:
            config (dict): Asset configuration dictionary

        Returns:
            int: phantom.APP_SUCCESS or phantom.APP_ERROR
        """
        self._connector.debug_print("Processing parameters for IQ for TD Insights polling")

        # Initialize parameters from config for IQ for TD Insights
        self._iq_for_td_status = config.get("iq_for_td_status", "ALL")
        self._iq_for_td_severity = config.get("iq_for_td_severity", "ALL")
        self._iq_for_td_name = config.get("iq_for_td_name", "")
        self._iq_for_td_threat_properties = config.get("iq_for_td_threat_properties", "")
        self._iq_for_td_date_created = config.get("iq_for_td_date_created", "")
        self._iq_for_td_insight_id = config.get("iq_for_td_insight_id", "")
        self._iq_for_td_indicators = config.get("iq_for_td_indicators", "")
        self._iq_for_td_assets = config.get("iq_for_td_assets", "")
        self._iq_for_td_user = config.get("iq_for_td_user", "")

        if self._iq_for_td_date_created and not self._connector.validator.validate_rfc3339_datetime(self._iq_for_td_date_created):
            return self._action_result.set_status(
                phantom.APP_ERROR,
                consts.ERROR_INVALID_RFC3339_DATETIME_FORMAT.format(key="iq_for_td_date_created"),
            )

        return phantom.APP_SUCCESS

    def _poll_iq_for_td_insights(self):
        """Poll for IQ for TD Insights from Infoblox.

        Constructs the API request and processes the response.
        No checkpointing is used since the API doesn't support time-based filtering.
        Deduplication is handled via insight_id using SOAR's built-in mechanisms.

        Returns:
            tuple: (phantom.APP_SUCCESS/APP_ERROR, API response data)
        """
        self._connector.save_progress("Polling for IQ for TD Insights")

        # Construct query parameters
        params = self._build_iq_for_td_insights_query_params()

        # Make the API request
        endpoint = consts.IQ_FOR_TD_INSIGHTS_ENDPOINT
        ret_val, response = self._connector.util.make_rest_call(
            endpoint=endpoint,
            action_result=self._action_result,
            method="get",
            params=params,
        )

        if phantom.is_fail(ret_val):
            self._connector.save_progress("Failed to fetch IQ for TD Insights")
            return ret_val, None

        # Validate response structure
        if not response or "insight_list" not in response:
            self._connector.save_progress(consts.ACTION_IQ_FOR_TD_INSIGHTS_EMPTY)
            return phantom.APP_SUCCESS, response

        insights = response.get("insight_list", [])
        if not insights:
            self._connector.save_progress(consts.ACTION_IQ_FOR_TD_INSIGHTS_EMPTY)
            return phantom.APP_SUCCESS, response

        self._connector.save_progress(consts.ACTION_IQ_FOR_TD_INSIGHTS_SUCCESS.format(count=len(insights)))

        if self._container_count is not None and len(insights) > self._container_count:
            self._connector.save_progress(
                f"Limiting ingestion to the requested maximum of {self._container_count} container(s) out of {len(insights)} insight(s) returned"
            )
            insights = insights[: self._container_count]

        # Process the response and create containers/artifacts
        ret_val, containers_created = self._process_iq_for_td_insights(insights)
        if phantom.is_fail(ret_val):
            return ret_val, None

        self._connector.save_progress(consts.ACTION_IQ_FOR_TD_INSIGHTS_CONTAINERS_CREATED.format(count=containers_created))

        return phantom.APP_SUCCESS, response

    def _build_iq_for_td_insights_query_params(self):
        """Build query parameters for the IQ for TD Insights API.

        Returns:
            dict: Query parameters for API request
        """
        params = {}

        # Add filtering parameters if provided - if 'ALL' is selected, don't add the parameter
        # so the API returns insights across all statuses/severity levels
        if self._iq_for_td_status and self._iq_for_td_status.lower() != "all":
            params["status"] = self._iq_for_td_status

        if self._iq_for_td_severity and self._iq_for_td_severity.lower() != "all":
            # The API expects title-cased severity values (Critical, High, Medium, Low),
            # while the asset config value_list stores them uppercase (e.g. "HIGH").
            params["severity"] = self._iq_for_td_severity.capitalize()

        if self._iq_for_td_name:
            params["name"] = self._iq_for_td_name

        if self._iq_for_td_threat_properties:
            params["threat_properties"] = self._iq_for_td_threat_properties

        if self._iq_for_td_date_created:
            params["date_created"] = self._iq_for_td_date_created

        if self._iq_for_td_insight_id:
            params["insight_id"] = self._iq_for_td_insight_id

        if self._iq_for_td_indicators:
            params["indicators"] = self._iq_for_td_indicators

        if self._iq_for_td_assets:
            params["assets"] = self._iq_for_td_assets

        if self._iq_for_td_user:
            params["user"] = self._iq_for_td_user

        self._connector.debug_print(f"IQ for TD Insights query parameters: {params}")
        return params

    def _process_iq_for_td_insights(self, insights):
        """Process the IQ for TD Insights response and create containers and artifacts.

        Args:
            insights (list): List of IQ for TD Insights from API response

        Returns:
            tuple: (phantom.APP_SUCCESS or phantom.APP_ERROR, containers_created_count)
        """
        if not insights:
            self._connector.save_progress("No IQ for TD Insights found in the response")
            return phantom.APP_SUCCESS, 0

        self._connector.save_progress(f"Processing {len(insights)} IQ for TD Insights")
        containers_created = 0

        # Process each insight and create a container with artifacts
        for i, insight in enumerate(insights):
            try:
                insight_id = insight.get("insight_id")
                if not insight_id:
                    self._connector.debug_print("Skipping insight without insight_id")
                    continue

                # Create (or reuse the duplicate of) the container for this insight
                container_id, is_duplicate = self._create_container_for_insight(insight)
                if container_id is None:
                    continue

                if not is_duplicate:
                    containers_created += 1
                    self._connector.debug_print(consts.CONTAINER_CREATED_MSG.format(insight_id=insight_id))

                # Create an artifact for this insight, unless the poll asked for no artifacts
                if self._artifact_count is None or self._artifact_count > 0:
                    artifact_id = self._create_artifact_for_insight(insight, container_id)
                    if artifact_id is not None:
                        self._connector.debug_print(consts.ARTIFACT_CREATED_MSG.format(insight_id=insight_id))

                if (i + 1) % 10 == 0:
                    self._connector.save_progress(f"Processed {i + 1} of {len(insights)} insights")

            except Exception as e:
                self._connector.debug_print(f"Error processing insight {insight.get('insight_id', 'unknown')}: {e!s}")
                continue

        self._connector.save_progress(f"Completed processing IQ for TD Insights. Created {containers_created} new containers.")
        return phantom.APP_SUCCESS, containers_created

    def _create_container_for_insight(self, insight):
        """Create a container for an IQ for TD Insight.

        Args:
            insight (dict): IQ for TD Insight data

        Returns:
            tuple: (container ID, whether SOAR matched an existing duplicate container), or
                (None, False) if the container could not be saved
        """
        try:
            # Generate container name as specified: name + '-' + insight_id
            name = insight.get("name", "Unknown")
            insight_id = insight.get("insight_id", "")
            container_name = f"{name}-{insight_id}"

            self._connector.debug_print(
                f"Creating container for insight {insight_id} with name {container_name} and severity {insight.get('severity', '')}"
            )
            # Map severity to container severity
            container_severity = self._map_severity(insight.get("severity", ""))
            container_status = self._map_status(insight.get("status", ""))

            # Generate source data identifier using insight_id for deduplication
            source_data_id = f"{consts.IQ_FOR_TD_INSIGHTS_CONTAINER_SOURCE_ID_KEY}_{insight_id}"

            # Create the container JSON
            container_json = {
                "name": container_name,
                "description": f"IQ for TD Insight: {name} - {insight_id}",
                "source_data_identifier": source_data_id,
                "severity": container_severity,
                "status": container_status,
                "label": self._connector.get_config().get("ingest", {}).get("container_label"),
                "data": insight,
                "tags": ["infoblox", "iq_for_td_insights"],
            }

            save_result = self._connector.save_container(container_json)

        except Exception as e:
            self._connector.debug_print(f"Error creating container: {e!s}")
            return None, False

        if save_result and len(save_result) == 3:
            ret_val, message, container_id = save_result
            if phantom.is_success(ret_val) and container_id is not None:
                is_duplicate = message == "Duplicate container found"
                self._connector.debug_print(f"{'Using existing' if is_duplicate else 'Successfully created'} container with ID: {container_id}")
                return container_id, is_duplicate
            self._connector.debug_print(f"Failed to create container: {message}")
        else:
            self._connector.debug_print("Unexpected return value from save_container")

        return None, False

    def _map_severity(self, severity):
        """Map IQ for TD Insight severity to Phantom container severity.

        Args:
            severity (str): Severity text from insight (LOW, MEDIUM, HIGH, CRITICAL)

        Returns:
            str: Phantom severity level
        """
        return consts.PHANTOM_SEVERITY_MAP.get(severity.upper(), "high")

    def _map_status(self, status):
        """Map IQ for TD Insight workflow status to a SOAR container status.

        Args:
            status (str): Status text from insight (e.g. Needs Review, In Progress, Resolved)

        Returns:
            str: SOAR container status (new, open, or closed)
        """
        return consts.PHANTOM_CONTAINER_STATUS_MAP.get(str(status).strip().upper(), consts.DEFAULT_CONTAINER_STATUS)

    @staticmethod
    def _format_cef_list(value):
        """Render a possibly list-valued insight field as a CEF-safe scalar.

        Args:
            value: Raw insight field value, which the API may return as a list

        Returns:
            str: Comma-joined string for list input, the original scalar otherwise
        """
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value)
        return "" if value is None else value

    def _create_artifact_for_insight(self, insight, container_id):
        """Create an artifact for an IQ for TD Insight.

        Args:
            insight (dict): IQ for TD Insight data
            container_id (int): The container ID to add the artifact to

        Returns:
            int: Artifact ID if successful, None otherwise
        """
        try:
            insight_id = insight.get("insight_id", "")
            name = insight.get("name", "")

            # Determine the artifact type
            artifact_type = "IQ for TD Insight Data"

            # Build CEF data with all available insight fields
            cef_data = {
                # Core Insight Information
                "Insight ID": insight_id,
                "Insight Name": name,
                "Description": insight.get("description", ""),
                "Status": insight.get("status", ""),
                "Severity": insight.get("severity", ""),
                # CEF values are consumed as scalars by playbooks and the artifact table, so join
                # the list form the API returns. The raw list stays in the artifact's `data`.
                "Threat Properties": self._format_cef_list(insight.get("threat_properties")),
                # Time Information
                "Date Created": insight.get("date_created", ""),
                "Evaluation Start Date": insight.get("evaluation_start_date", ""),
                "Evaluation End Date": insight.get("evaluation_end_date", ""),
                "Expiring In Days": insight.get("expiring_in_days", ""),
                # Event & Asset Statistics
                "Total Events": insight.get("total_events", ""),
                "Total Assets": insight.get("total_assets", ""),
                "Total Indicators": insight.get("total_indicators", ""),
                "Total Users": insight.get("total_users", ""),
                # Efficiency Metric
                "Time Saved (Seconds)": insight.get("time_saved_seconds", ""),
                # Device Info
                "Device Vendor": "Infoblox",
                "Device Product": "Infoblox Cloud",
            }

            # Generate source data identifier for the artifact
            source_data_id = f"iq_for_td_insight_artifact_{insight_id}"

            artifact_severity = self._map_severity(insight.get("severity", ""))

            # Create the artifact JSON
            artifact_json = {
                "name": f"IQ for TD Insight Data - {name}-{insight_id}",
                "label": "iq_for_td_insight_data",
                "container_id": container_id,
                "source_data_identifier": source_data_id,
                "cef": cef_data,
                "type": artifact_type,
                "data": insight,
                "run_automation": True,
                "severity": artifact_severity,
                "tags": ["infoblox", "iq_for_td_insights"],
            }

            save_result = self._connector.save_artifact(artifact_json)

        except Exception as e:
            self._connector.debug_print(f"Error creating artifact: {e!s}")
            return None

        if save_result and len(save_result) == 3:
            ret_val, message, artifact_id = save_result
            if phantom.is_success(ret_val) and artifact_id is not None:
                return artifact_id
            self._connector.debug_print(f"Failed to save artifact: {message}")
        else:
            self._connector.debug_print("Unexpected return value from save_artifact")

        return None
