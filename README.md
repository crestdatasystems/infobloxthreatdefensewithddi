# Infoblox Threat Defense with DDI

Publisher: Infoblox <br>
Connector Version: 2.0.0 <br>
Product Vendor: Infoblox <br>
Product Name: Infoblox Threat Defense with DDI <br>
Minimum Product Version: 6.4.1

This app integrates with Infoblox Threat Defense with DDI to provide DNS security, threat intelligence, and centralized DDI (DNS, DHCP, and IP Address Management) capabilities. It enables automated lookups of IP and host asset data, and management of custom lists for security policies.

# Explanation of Data Ingestion

This integration supports two types of data ingestion: **DNS Security Events** and **IQ for TD Insights**. If an ingestion type is not selected while configuring asset, the integration defaults to ingesting **DNS Security Events**. Only one data ingestion type can be configured per asset. To configure multiple data ingestions, set up multiple assets.

The below details describe the configuration and usage of the Infoblox integration for Splunk SOAR, focusing on the two on-poll ingestion types: **DNS Security Events** and **IQ for TD Insights**.

______________________________________________________________________

## Migrating from SOC Insights

Release **2.0.0** renames the SOC Insights capability to **IQ for TD Insights**, matching Infoblox's current product terminology, and moves it onto the Infoblox Insights v2 API. This is a **breaking change**: Splunk SOAR resolves asset configuration keys and playbook action blocks by name, so existing assets and playbooks keep working only after the updates below are applied.

### Impact

**Asset configuration.** The ingestion type value and all SOC filter parameters are renamed. The previously configured values are *not* migrated automatically, and the accepted values changed for status and priority/severity:

| Removed (1.x) | Replacement (2.0.0) | Value change |
|---------------|---------------------|--------------|
| Ingestion type `SOC Insights` | Ingestion type `IQ for TD Insights` | Re-select the ingestion type |
| `soc_status` (`Active`, `Closed`) | `iq_for_td_status` (`ALL`, `Needs Review`, `In Progress`, `Resolved`, `Accepted Risk`, `False Positive`) | `Active` maps to `Needs Review`/`In Progress`; `Closed` maps to `Resolved`/`Accepted Risk`/`False Positive`. Select `ALL` to keep ingesting every insight |
| `soc_priority` (`ALL`, `LOW`, `INFO`, `MEDIUM`, `HIGH`, `CRITICAL`) | `iq_for_td_severity` (`ALL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) | `INFO` no longer exists; use `LOW` |
| `soc_threat_type` | `iq_for_td_threat_properties` | Now a comma-separated threat-property list (e.g. `malware,phishing,ransomware`) |

The following filters are new and optional: `iq_for_td_name`, `iq_for_td_date_created`, `iq_for_td_insight_id`, `iq_for_td_indicators`, `iq_for_td_assets`, and `iq_for_td_user`.

**Actions.** Playbooks referencing the old action names or their renamed parameters will fail until updated:

| Removed (1.x) | Replacement (2.0.0) | Parameter changes |
|---------------|---------------------|-------------------|
| `get soc insights assets` | `get iq for td insights assets` | `asset_ip` becomes `ip_address`; `mac_address`, `os_version`, `user`, `from`, and `to` are removed; `device_name`, `indicators`, `users`, and `is_verified` are new |
| `get soc insights indicators` | `get iq for td insights indicators` | `confidence`, `indicator`, `actor`, `action`, `from`, and `to` are removed; `indicators`, `threat_level`, `status`, `users`, and `detected_at` are new |
| `get soc insights events` | `get iq for td insights events` | `from`/`to` become `detected_from`/`detected_to`; `confidence_level` becomes `threat_confidence`; `query_type` is removed; `tclass`, `device_name`, and `user` are new |
| `get soc insights comments` | *(no replacement)* | Use the `comment` parameter on `update iq for td insight status` to record analyst notes |

All date-time parameters now require **RFC 3339** values (e.g. `2025-12-19T03:00:00Z`) instead of the previous `YYYY-MM-DDTHH:mm:ss.SSS` form.

These actions are new in 2.0.0: `get iq for td insight details`, `update iq for td insight status`, `execute iq for td recommendation action`, and `undo iq for td recommendation action`.

**Ingested data.** Insight API fields are now snake_case (`insight_id`, `threat_properties`) rather than camelCase (`insightId`, `tFamily`), and container names change from `<threatType>-<tFamily>` to `<name>-<insight_id>` for newly ingested insights. Insights already ingested by an earlier release are matched to their existing container by insight ID instead of creating a new one: that container keeps its 1.x name, status, and artifact, and the first 2.0.0 poll adds a new `IQ for TD Insight Data` artifact to it, which can trigger active playbooks. Custom automation reading insight artifact CEF or container data must be updated to the new field names.

### Upgrade procedure

1. Note the current SOC filter values for every asset that ingests SOC Insights, and list the playbooks that reference the `get soc insights *` actions.
1. Install release 2.0.0.
1. For each affected asset, open **Asset Settings**, select the **IQ for TD Insights** ingestion type, and re-enter the filters using the replacement parameters in the table above.
1. Run **Poll Now** with a small **Maximum containers** value and confirm containers are created with the expected severity and status before re-enabling scheduled polling.
1. Update each playbook: rename the `get soc insights *` action blocks, remap the changed parameters, and replace any `get soc insights comments` block with `update iq for td insight status` using its `comment` parameter.
1. Update any custom automation that reads insight artifact CEF fields or container data to the snake_case field names.

______________________________________________________________________

## On-Poll Configuration

### Poll Now Feature

The **Poll Now** action retrieves the data based on the **Max Hours Backwards** parameter which is default set to 24 hours for ingestion type **DNS Security Events**.

**Important Notes:**

- The *Poll Now* feature **ignores** the **Source ID** parameter.
- For ingestion type **DNS Security Events**, the *Poll Now* feature also **ignores** the **Maximum containers** and **Maximum artifacts** parameters; the asset's **Limit** parameter bounds the run instead.
- For ingestion type **IQ for TD Insights**, **Maximum containers** caps the number of insights ingested in the run, and setting **Maximum artifacts** to `0` ingests containers without artifacts.
- The *Poll Now* feature does **not** store a checkpoint file, meaning it will fetch data according to the configured parameters without considering previous ingestions.

### Scheduled / Interval Polling

**Recommended Ingestion:**\
To optimize ingestion and reduce the volume of unnecessary events, it is strongly recommended to apply the maximum number of relevant filters. This ensures efficient processing and minimizes noise in the Splunk SOAR environment.

**Limit Parameter:**\
The `limit` parameter controls the maximum number of records ingested per poll. The default value is **100**; adjust based on your requirements.

**Max Hours Backwards Parameter:**\
For the first poll, this parameter determines how many hours of historical data to fetch. For subsequent polls, the integration uses the timestamp from the last poll as the starting point.

______________________________________________________________________

## DNS Security Events

- **Parameters:**

  - **Max Hours Backwards:** Number of hours before the first connector iteration to retrieve alerts from (integer, default: 24).
  - **Queried name:** Filter by comma-separated queried domain names (string list).
  - **Policy Name:** Filter by comma-separated security policy names (string list).
  - **Threat Level:** Filter by threat severity level (LOW, MEDIUM, HIGH) (string).
  - **Threat Class:** Filter by comma-separated threat category (e.g., "Malware", "MalwareDownload") (string list).
  - **Threat Family:** Filter by comma-separated threat family (e.g., Log4Shell, OPENRESOLVER) (string).
  - **Threat Indicator:** Filter by comma-separated threat indicators (domains, IPs) (string list).
  - **Policy Action:** Filter by comma-separated action performed (Log, Block, Default, Redirect) (string list).
  - **Feed Name:** Filter by comma-separated threat feed or custom list name (string list).
  - **Network:** Filter by comma-separated network name, on-premises host, endpoint, or DFP name (string list).
  - **Limit:** Maximum number of records to retrieve per polling cycle (integer, default: 100).

- **Severity Mapping of DNS Security Events:**

  | Threat Level | SOAR Container Severity |
  |--------------|------------------------|
  | HIGH | High |
  | MEDIUM | Medium |
  | LOW | Low |
  | INFO | Low |

- **Container Creation:**\
  Each DNS Security Event will create a separate container in Splunk SOAR with relevant metadata and artifacts containing the event details.

- **Important API Limitation:**\
  The DNS Security Events API does not support sorting, and records are returned in descending order by default. This may result in data loss if there are more records than the specified limit. To minimize this risk, apply relevant filters and adjust the limit parameter appropriately.

______________________________________________________________________

## IQ for TD Insights

- **Parameters:**

  - **Status:** Filter Insights by their current status. Defaults to `ALL`; when `ALL` is selected, no status filter is sent to the API (string).
  - **Severity:** Filter Insights by severity level (LOW, MEDIUM, HIGH, CRITICAL). Defaults to `ALL`; when `ALL` is selected, no severity filter is sent to the API (string).
  - **Name:** Filter by the user-facing insight name (case-insensitive partial match) (string).
  - **Threat Properties:** Filter by comma-separated threat properties, e.g. `malware,phishing,ransomware` (string).
  - **Date Created:** Filter by the insight creation timestamp. Provide an RFC 3339 date-time value (e.g., `2025-12-19T07:01:56Z`); only insights created on that specific day are returned; this is a single-day filter, not a range from this date to now (string).
  - **Insight ID:** Return a specific insight by its unique display identifier (string).
  - **Indicators:** Filter by comma-separated threat indicators; matches insights whose indicators array contains any of the listed values (string).
  - **Assets:** Filter by comma-separated assets; matches insights whose assets array contains any of the listed values (string).
  - **User:** Filter by comma-separated users; matches insights whose users array contains any of the listed values (string).

- **Severity Mapping of IQ for TD Insights:**

  | Severity Level | SOAR Container Severity |
  |----------------|------------------------|
  | CRITICAL | High |
  | HIGH | High |
  | MEDIUM | Medium |
  | LOW | Low |

- **Status Mapping of IQ for TD Insights:**

  Infoblox is the system of record for the insight workflow, so the insight status is mirrored onto the SOAR container when it is created. An insight that is already closed in Infoblox is still ingested, but as a closed container rather than a new one. The status is not updated for containers that already exist.

  | Insight Status | SOAR Container Status |
  |----------------|----------------------|
  | Needs Review | New |
  | In Progress | Open |
  | Resolved | Closed |
  | Accepted Risk | Closed |
  | False Positive | Closed |

- **Container Creation:**\
  Each IQ for TD Insight will create a separate container in Splunk SOAR with relevant metadata and artifacts containing the insight details.

- **Container Updates:**\
  IQ for TD Insight containers and artifacts will not be updated after initial ingestion, even if the insight is updated in Infoblox.

- **Insight Deduplication:**\
  Insights will be deduplicated based on the insight ID to prevent duplicate containers.

______________________________________________________________________

## Best Practices

- **Filtering Recommendations:**\
  To optimize ingestion and reduce the volume of unnecessary events, it is strongly recommended to apply the maximum number of relevant filters. This ensures efficient processing and minimizes noise in the Splunk SOAR environment.

- **Time-based Polling:**\
  DNS Security Events ingestion type uses time-based filtering for incremental polling. The timestamp of the last fetched event will be used as the new polling start time, ensuring only new events are ingested in subsequent polls.

- **Multiple Assets Configuration:**\
  For organizations that need to ingest both DNS Security Events and IQ for TD Insights simultaneously, configure two separate assets, one for each ingestion type.

______________________________________________________________________

## Playbooks

- Playbooks for **Infoblox Threat Defense with DDI** are available in the [repository](https://github.com/infobloxopen/infoblox_splunk_soar/tree/main/Infoblox%20Threat%20Defense%20with%20DDI). Refer to the README for detailed instructions on setup and configuration.

______________________________________________________________________

### Configuration variables

This table lists the configuration variables required to operate Infoblox Threat Defense with DDI. These variables are specified when configuring a Infoblox Threat Defense with DDI asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL for Infoblox API (e.g., https://csp.infoblox.com) |
**api_key** | required | password | API Key for authentication |
**ingestion_type** | optional | string | Type of data to retrieve and ingest |
**queried_name** | optional | string | Filter by comma-separated queried domain names (DNS Security Events) |
**policy_name** | optional | string | Filter by comma-separated security policy names (DNS Security Events) |
**threat_level** | optional | string | Filter by threat severity level (DNS Security Events) |
**threat_class** | optional | string | Filter by comma-separated threat class (DNS Security Events) |
**threat_family** | optional | string | Filter by comma-separated threat family (DNS Security Events) |
**threat_indicator** | optional | string | Filter by comma-separated threat indicators (domains, IPs) (DNS Security Events) |
**policy_action** | optional | string | Filter by comma-separated action performed (Log, Block, Default, Redirect) (DNS Security Events) |
**feed_name** | optional | string | Filter by comma-separated threat feed or custom list name (DNS Security Events) |
**network** | optional | string | Filter by comma-separated network name, on-premises host, endpoint, or DFP name (DNS Security Events) |
**limit** | optional | numeric | Specify the maximum number of events to fetch (default: 100) (DNS Security Events) |
**max_hours_backwards** | optional | numeric | Specify the number of hours of historical data to retrieve for manual polling (default: 24 hours) (DNS Security Events) |
**iq_for_td_status** | optional | string | Filter by IQ for TD Insight status (Infoblox IQ for TD Insight) |
**iq_for_td_name** | optional | string | Filter by insight name (case-insensitive partial match) (Infoblox IQ for TD Insight) |
**iq_for_td_severity** | optional | string | Filter by IQ for TD Insight severity level (Infoblox IQ for TD Insight) |
**iq_for_td_threat_properties** | optional | string | Filter by comma-separated threat properties (e.g. malware,phishing,ransomware) (Infoblox IQ for TD Insight) |
**iq_for_td_date_created** | optional | string | Return insights created on this RFC 3339 date (e.g. 2025-12-19T07:01:56Z); only records for that specific day are returned, not a range from this date to now (Infoblox IQ for TD Insight) |
**iq_for_td_insight_id** | optional | string | Return a specific insight by its unique identifier (Infoblox IQ for TD Insight) |
**iq_for_td_indicators** | optional | string | Filter by comma-separated threat indicators (Infoblox IQ for TD Insight) |
**iq_for_td_assets** | optional | string | Filter by comma-separated assets (Infoblox IQ for TD Insight) |
**iq_for_td_user** | optional | string | Filter by comma-separated users (Infoblox IQ for TD Insight) |

### Supported Actions

[on poll](#action-on-poll) - Ingest data from Infoblox (DNS Security Events or IQ for TD Insights based on configuration) <br>
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[initiate indicator intel lookup](#action-initiate-indicator-intel-lookup) - Initiate an indicator investigation using Infoblox Dossier <br>
[get indicator intel lookup result](#action-get-indicator-intel-lookup-result) - Retrieve the result of a previously initiated Dossier lookup for an indicator (IP/URL/Host/MAC/Hash) <br>
[ip asset data lookup](#action-ip-asset-data-lookup) - Look up asset data for a given IP address using IPAM address information <br>
[get custom list](#action-get-custom-list) - Retrieve Custom Lists from Infoblox by ID, name, or filtering criteria <br>
[remove custom list](#action-remove-custom-list) - Delete a Custom List from Infoblox Cloud <br>
[create network list](#action-create-network-list) - Create a Network List with specified name, items, and optional description <br>
[update network list](#action-update-network-list) - Update metadata and CIDRs of a specified network list <br>
[get network list](#action-get-network-list) - Retrieve network lists and their metadata <br>
[get iq for td insights assets](#action-get-iq-for-td-insights-assets) - Retrieve the list of associated assets for a given Insight ID <br>
[remove network list](#action-remove-network-list) - Remove a specific network list by ID <br>
[host asset data lookup](#action-host-asset-data-lookup) - Look up host asset data using IPAM host information to retrieve detailed host information from Infoblox <br>
[dns record lookup](#action-dns-record-lookup) - Perform a DNS record query to retrieve associated IPs or domains from Infoblox DDI <br>
[dhcp lease lookup](#action-dhcp-lease-lookup) - Perform a DHCP lease query to retrieve lease information from Infoblox DDI <br>
[indicator threat lookup](#action-indicator-threat-lookup) - Lookup threat intelligence details for an indicator using Infoblox TIDE <br>
[create custom list](#action-create-custom-list) - Create a new custom list with specified details and items <br>
[update custom list](#action-update-custom-list) - Update metadata of an existing custom list such as name, description, confidence level, threat level, or tags <br>
[remove security policy](#action-remove-security-policy) - Remove a specific Security Policy by Security Policy ID <br>
[get security policy](#action-get-security-policy) - Retrieve Security Policies and their metadata <br>
[create security policy](#action-create-security-policy) - Create a Security Policy, including its name, rules, associated network lists, DNS Forwarding Proxies (DFPs) etc <br>
[update custom list items](#action-update-custom-list-items) - Insert or remove individual items (e.g., IPs, domains) in a custom list <br>
[update security policy](#action-update-security-policy) - Update a specific Security Policy, including its name, rules, associated network lists, DNS Forwarding Proxies (DFPs) etc <br>
[get iq for td insights indicators](#action-get-iq-for-td-insights-indicators) - Retrieve a filtered list of indicators associated with a specific Insight ID from Infoblox, supporting multiple filter parameters <br>
[get iq for td insights events](#action-get-iq-for-td-insights-events) - Retrieve a detailed list of threat-related events for a specific Insight ID from Infoblox IQ for TD Insights <br>
[get iq for td insight details](#action-get-iq-for-td-insight-details) - Retrieve the full detail view for a single IQ for TD Insight, including counts, severity, top indicators/assets, threat actors, and recommendations <br>
[update iq for td insight status](#action-update-iq-for-td-insight-status) - Update the workflow status of a specific IQ for TD Insight, optionally recording an analyst comment describing the change <br>
[execute iq for td recommendation action](#action-execute-iq-for-td-recommendation-action) - Execute a single recommendation action on an IQ for TD Insight, referencing the recommendation by the ID returned in the 'get iq for td insight details' action <br>
[undo iq for td recommendation action](#action-undo-iq-for-td-recommendation-action) - Reverse a previously executed recommendation action using the audit entry ID returned by the 'execute iq for td recommendation action' action

## action: 'on poll'

Ingest data from Infoblox (DNS Security Events or IQ for TD Insights based on configuration)

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'initiate indicator intel lookup'

Initiate an indicator investigation using Infoblox Dossier

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**indicator_type** | required | Specify the type of indicator to search for | string | |
**indicator_value** | required | Specify the indicator value(s) based on the indicator type you want to search for | string | `ip` `ipv6` `url` `email` `hash` `host name` |
**source** | optional | Specify the comma-separated sources to query | string | |
**wait_for_results** | optional | If set to true, the call will wait for results to complete else return the jobID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.indicator_type | string | | Host IP |
action_result.parameter.indicator_value | string | `ip` `ipv6` `url` `email` `hash` `host name` | 1.1.1.1 |
action_result.parameter.source | string | | atp gcs |
action_result.parameter.wait_for_results | string | | true false |
action_result.data.\*.job.id | string | | 2e14fe00-38e0-4707-bd53-44cc00108cc0 |
action_result.data.\*.results.\*.data.A.\*.ip | string | | 142.251.16.101 |
action_result.data.\*.results.\*.data.A.\*.reverse | string | | bl-in-f101.1e100.net. |
action_result.data.\*.results.\*.data.A.\*.ttl | numeric | | 297 |
action_result.data.\*.results.\*.data.actor_description | string | | Google Search is a fully-automated search engine. |
action_result.data.\*.results.\*.data.actor_id | string | | ca3db41a-9419-4a23-a179-f8661d4548a1 |
action_result.data.\*.results.\*.data.actor_name | string | | Google Search |
action_result.data.\*.results.\*.data.asn_num | string | | 13335 |
action_result.data.\*.results.\*.data.attack_chain.command_and_control | string | | |
action_result.data.\*.results.\*.data.attack_chain.\*.category | string | | Technique |
action_result.data.\*.results.\*.data.attack_chain.\*.description | string | | |
action_result.data.\*.results.\*.data.attack_chain.\*.detection | string | | |
action_result.data.\*.results.\*.data.attack_chain.\*.external_reference.\*.description | string | | |
action_result.data.\*.results.\*.data.attack_chain.\*.external_reference.\*.external_id | string | | T1056 |
action_result.data.\*.results.\*.data.attack_chain.\*.external_reference.\*.source_name | string | | mitre-attack |
action_result.data.\*.results.\*.data.attack_chain.\*.external_reference.\*.url | string | | https://attack.mitre.org/techniques/T1056 |
action_result.data.\*.results.\*.data.attack_chain.\*.id | string | | IC |
action_result.data.\*.results.\*.data.attack_chain.\*.name | string | | Input Capture |
action_result.data.\*.results.\*.data.attack_chain.\*.version | string | | 1.0 |
action_result.data.\*.results.\*.data.attack_chain.lateral_movement | string | | |
action_result.data.\*.results.\*.data.attack_chain.persistence | string | | |
action_result.data.\*.results.\*.data.attack_chain.privilege_escalation | string | | |
action_result.data.\*.results.\*.data.category_name | string | | Search Engines |
action_result.data.\*.results.\*.data.city | string | | Sydney |
action_result.data.\*.results.\*.data.country_code | string | | AU |
action_result.data.\*.results.\*.data.country_name | string | | Australia |
action_result.data.\*.results.\*.data.customer_first_dns_query | string | | 2021-07-01 |
action_result.data.\*.results.\*.data.customer_last_dns_query | string | | 2025-07-28 |
action_result.data.\*.results.\*.data.date_captured | string | | 2025-07-23 00:52:46 |
action_result.data.\*.results.\*.data.display_name | string | | Google Search |
action_result.data.\*.results.\*.data.domain | string | | google.com |
action_result.data.\*.results.\*.data.hostname | string | | google.com |
action_result.data.\*.results.\*.data.ikb_first_classified_malicious | string | | |
action_result.data.\*.results.\*.data.ikb_submitted | string | | 2022-03-22T11:25:55.000Z |
action_result.data.\*.results.\*.data.image | string | | |
action_result.data.\*.results.\*.data.impacted_devices.\*.deviceCount | numeric | | 8 |
action_result.data.\*.results.\*.data.impacted_devices.\*.device_name | string | | 82.140.0.80 |
action_result.data.\*.results.\*.data.impacted_devices.\*.network | string | | CREST_DFP (DFP) |
action_result.data.\*.results.\*.data.impacted_devices.\*.qip | string | | 82.140.0.80 |
action_result.data.\*.results.\*.data.impacted_devices.\*.timestamp | string | | 1753665659 |
action_result.data.\*.results.\*.data.info | string | | bad http status |
action_result.data.\*.results.\*.data.interval | string | | [49, 67] |
action_result.data.\*.results.\*.data.is_valid | boolean | | True False |
action_result.data.\*.results.\*.data.is_valid_chain.is_valid | boolean | | True False |
action_result.data.\*.results.\*.data.isp | string | | Cloudflare, Inc. |
action_result.data.\*.results.\*.data.issuer | string | | GlobalSign Root CA |
action_result.data.\*.results.\*.data.latitude | numeric | | -33.8688 |
action_result.data.\*.results.\*.data.longitude | numeric | | 151.209 |
action_result.data.\*.results.\*.data.matches.\*.confidence | string | | high |
action_result.data.\*.results.\*.data.matches.\*.domain | string | | ns1.google.com |
action_result.data.\*.results.\*.data.matches.\*.malicious_counts | string | | 229974 |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_confidence | string | | high |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_label | string | | Very Low Risk |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_malicious_counts | string | | 0 |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_popular | string | | False |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_rare | string | | True |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_raw_score | string | | -inf |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_score | string | | 0 |
action_result.data.\*.results.\*.data.matches.\*.ns_reputation_total_counts | string | | 638 |
action_result.data.\*.results.\*.data.matches.\*.popular | string | | True |
action_result.data.\*.results.\*.data.matches.\*.rare | string | | False |
action_result.data.\*.results.\*.data.matches.\*.raw_score | string | | -3.7113174165239293 |
action_result.data.\*.results.\*.data.matches.\*.score | string | | 5 |
action_result.data.\*.results.\*.data.matches.\*.score_label | string | | Moderate Risk |
action_result.data.\*.results.\*.data.matches.\*.tld | string | | com |
action_result.data.\*.results.\*.data.matches.\*.total_counts | string | | 9637673 |
action_result.data.\*.results.\*.data.org | string | | |
action_result.data.\*.results.\*.data.page | string | | 1 |
action_result.data.\*.results.\*.data.postal_code | string | | 1001 |
action_result.data.\*.results.\*.data.ptr_record | string | | one.one.one.one |
action_result.data.\*.results.\*.data.rank | numeric | | 55 |
action_result.data.\*.results.\*.data.raw_cert | string | | |
action_result.data.\*.results.\*.data.rcode | string | | NOERROR |
action_result.data.\*.results.\*.data.reason | string | | bad api response status code: 401 |
action_result.data.\*.results.\*.data.record_count | numeric | | 71 |
action_result.data.\*.results.\*.data.records.\*.class | string | | InternetInfrastructure |
action_result.data.\*.results.\*.data.records.\*.detected | string | | 2024-10-10T17:58:08Z |
action_result.data.\*.results.\*.data.records.\*.expiration | string | | 2025-10-10T17:58:08Z |
action_result.data.\*.results.\*.data.records.\*.feed_name | string | | ib-low-block |
action_result.data.\*.results.\*.data.records.\*.indicator | string | | 1.1.1.1 |
action_result.data.\*.results.\*.data.records.\*.property | string | | InternetInfrastructure_DoHService |
action_result.data.\*.results.\*.data.records.\*.threat_level | numeric | | |
action_result.data.\*.results.\*.data.region | string | | New South Wales |
action_result.data.\*.results.\*.data.related_count | string | | 190 |
action_result.data.\*.results.\*.data.requests_by_day.\*.requests | numeric | | 2 |
action_result.data.\*.results.\*.data.requests_by_day.\*.timestamp | string | | 1751241600 |
action_result.data.\*.results.\*.data.response.ip_response | string | | |
action_result.data.\*.results.\*.data.response.parsed_whois.contacts | string | | |
action_result.data.\*.results.\*.data.response.parsed_whois.created_date | string | | 1997-09-15T04:00:00Z |
action_result.data.\*.results.\*.data.response.parsed_whois.domain | string | | GOOGLE.COM |
action_result.data.\*.results.\*.data.response.parsed_whois.expired_date | string | | 2028-09-14T04:00:00Z |
action_result.data.\*.results.\*.data.response.parsed_whois.other_properties.registry_domain_id | string | | 2138514_DOMAIN_COM-VRSN |
action_result.data.\*.results.\*.data.response.parsed_whois.registrar.abuse_contact_email | string | | |
action_result.data.\*.results.\*.data.response.parsed_whois.registrar.abuse_contact_phone | string | | |
action_result.data.\*.results.\*.data.response.parsed_whois.registrar.iana_id | string | | 292 |
action_result.data.\*.results.\*.data.response.parsed_whois.registrar.name | string | | MarkMonitor Inc. |
action_result.data.\*.results.\*.data.response.parsed_whois.updated_date | string | | 2019-09-09T15:39:04Z |
action_result.data.\*.results.\*.data.response.raw | string | | |
action_result.data.\*.results.\*.data.response.registrant | string | | MarkMonitor Inc. |
action_result.data.\*.results.\*.data.response.registration.created | string | | 1997-09-15T04:00:00Z |
action_result.data.\*.results.\*.data.response.registration.expires | string | | 2028-09-14T04:00:00Z |
action_result.data.\*.results.\*.data.response.registration.registrar | string | | MarkMonitor Inc. |
action_result.data.\*.results.\*.data.response.registration.updated | string | | 2019-09-09T15:39:04Z |
action_result.data.\*.results.\*.data.response.whois.date | string | | 2025-07-30 |
action_result.data.\*.results.\*.data.response.whois.record | string | | |
action_result.data.\*.results.\*.data.results.\*.confidence_level | string | | HIGH |
action_result.data.\*.results.\*.data.results.\*.created_time | string | | 2025-07-29T06:11:10Z |
action_result.data.\*.results.\*.data.results.\*.description | string | | Global list of known malicious domains for all sites. |
action_result.data.\*.results.\*.data.results.\*.id | numeric | | 834468 |
action_result.data.\*.results.\*.data.results.\*.item_count | numeric | | 2 |
action_result.data.\*.results.\*.data.results.\*.threat_level | string | | HIGH |
action_result.data.\*.results.\*.data.results.\*.type | string | | custom_list |
action_result.data.\*.results.\*.data.results.\*.updated_time | string | | 2025-07-29T06:28:45Z |
action_result.data.\*.results.\*.data.results.\*.description | string | | Google Search is a fully-automated search engine. |
action_result.data.\*.results.\*.data.results.\*.labels.category | string | | |
action_result.data.\*.results.\*.data.results.\*.labels.subcategory | string | | |
action_result.data.\*.results.\*.data.results.\*.name | string | | Search Engines |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.expires | string | | 2025-September-29 |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.issuer.common_name | string | | WR2 |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.public_key_algorithm | string | | ECDSA |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.serial_number | string | | 104690999963482091989177059696995060279 |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.signature_algorithm | string | | SHA256-RSA |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.subject.common_name | string | | \*.google.com |
action_result.data.\*.results.\*.data.ssl_cert_chain.\*.version | numeric | | 3 |
action_result.data.\*.results.\*.data.status | string | | No match |
action_result.data.\*.results.\*.data.threat.\*.batch_id | string | | d78fde3c-d456-11ee-8c27-75dfebb61a1a |
action_result.data.\*.results.\*.data.threat.\*.class | string | | Phishing |
action_result.data.\*.results.\*.data.threat.\*.confidence | numeric | | 100 |
action_result.data.\*.results.\*.data.threat.\*.confidence_score | numeric | | 8 |
action_result.data.\*.results.\*.data.threat.\*.confidence_score_rating | string | | High |
action_result.data.\*.results.\*.data.threat.\*.confidence_score_vector | string | | COSIS:1.0/SR:H/POP:N/TLD:N/CP:F |
action_result.data.\*.results.\*.data.threat.\*.detected | string | | 2024-02-26T03:23:49.295Z |
action_result.data.\*.results.\*.data.threat.\*.domain | string | | google.com |
action_result.data.\*.results.\*.data.threat.\*.expiration | string | | 2024-06-25T03:23:49.295Z |
action_result.data.\*.results.\*.data.threat.\*.extended.attack_chain | string | | ACIS:1.0/FWK:MTK/PLT:['M', 'W', 'L']/IA:{SA:[]},{SL:[]},{SVS:[]}/EXE:{CHF:[]},{UE:[]}/DE:{CHF:[]}/COLL:{IC:['EMP', 'POSH', 'POWS', 'REMC', 'PUP', 'QRAT', 'COBS']} |
action_result.data.\*.results.\*.data.threat.\*.extended.confidence_score | string | | {"rating": "High", "vector": "CSS:1.0/SR:H/POP:N/TLD:N/CP:F", "score": "7.72"} |
action_result.data.\*.results.\*.data.threat.\*.extended.cyberint_guid | string | | 98a7696ca30bd22aaed188aa9b8ea805 |
action_result.data.\*.results.\*.data.threat.\*.extended.extended | string | | b5ade1e0dfc2ce7550e1bee3bd0e3623https |
action_result.data.\*.results.\*.data.threat.\*.extended.from_email | string | | "Kinneys Automotive Service" <noreply@demandforced3.com> |
action_result.data.\*.results.\*.data.threat.\*.extended.no_whitelist | string | | false |
action_result.data.\*.results.\*.data.threat.\*.extended.notes | string | | Indicators associated with phishing campaign targeting Miles & More |
action_result.data.\*.results.\*.data.threat.\*.extended.protocol | string | | http |
action_result.data.\*.results.\*.data.threat.\*.extended.references | string | | https://urlscan.io/result/bd4e198d-b413-4951-bfab-000206285185/ |
action_result.data.\*.results.\*.data.threat.\*.extended.risk_score | string | | {"rating": "High", "vector": "RSS:1.0/TSS:M/TLD:N/CVSS:L/EX:H/MOD:N/AVL:N/T:M/DT:L", "score": "7.85"} |
action_result.data.\*.results.\*.data.threat.\*.extended.subject_line | string | | The hottest months are here - is your car overheating? |
action_result.data.\*.results.\*.data.threat.\*.extended.threat_score | string | | {"rating": "Medium", "vector": "TSS:1.0/AV:N/AC:L/PR:L/UI:R/EX:H/MOD:N/AVL:N/CI:N/ASN:H/TLD:N/DOP:N/P:F", "score": "6.0"} |
action_result.data.\*.results.\*.data.threat.\*.full_profile | string | | IID:IB_NOC |
action_result.data.\*.results.\*.data.threat.\*.hash | string | | 447163012e9a41fdcca93e947b0ced12201547a13ecccd3efa2a07d0baa45cb2 |
action_result.data.\*.results.\*.data.threat.\*.hash_type | string | | SHA256 |
action_result.data.\*.results.\*.data.threat.\*.host | string | | google.com |
action_result.data.\*.results.\*.data.threat.\*.id | string | | d79387bd-d456-11ee-8c27-75dfebb61a1a |
action_result.data.\*.results.\*.data.threat.\*.imported | string | | 2024-02-26T03:26:34.411Z |
action_result.data.\*.results.\*.data.threat.\*.profile | string | | IID |
action_result.data.\*.results.\*.data.threat.\*.property | string | | Phishing_Generic |
action_result.data.\*.results.\*.data.threat.\*.received | string | | 2024-02-26T03:26:34.411Z |
action_result.data.\*.results.\*.data.threat.\*.risk_score | numeric | | 8 |
action_result.data.\*.results.\*.data.threat.\*.risk_score_rating | string | | High |
action_result.data.\*.results.\*.data.threat.\*.risk_score_vector | string | | RSIS:1.0/TSS:M/TLD:N/CVSS:M/EX:H/MOD:N/AVL:N/T:M/DT:L |
action_result.data.\*.results.\*.data.threat.\*.threat_level | numeric | | 100 |
action_result.data.\*.results.\*.data.threat.\*.threat_score | numeric | | 6.5 |
action_result.data.\*.results.\*.data.threat.\*.threat_score_rating | string | | Medium |
action_result.data.\*.results.\*.data.threat.\*.threat_score_vector | string | | TSIS:1.0/AV:N/AC:L/PR:N/UI:R/EX:H/MOD:N/AVL:N/CI:N/ASN:N/TLD:N/DOP:N/P:F |
action_result.data.\*.results.\*.data.threat.\*.tld | string | | com |
action_result.data.\*.results.\*.data.threat.\*.type | string | | URL |
action_result.data.\*.results.\*.data.threat.\*.up | string | | true |
action_result.data.\*.results.\*.data.threat.\*.url | string | | http://google.com/amp/s/kuretid.cj-plus.de/2591-DE-43663/3004-DE-83582 |
action_result.data.\*.results.\*.data.url_title | string | | Google |
action_result.data.\*.results.\*.data.valid_after | string | | 2028-01-28 00:00:42 |
action_result.data.\*.results.\*.data.valid_before | string | | 2020-06-19 00:00:42 |
action_result.data.\*.results.\*.data.value | string | | 1.1.1.1 |
action_result.data.\*.results.\*.data.whitelisted | boolean | | True False |
action_result.data.\*.results.\*.params.target | string | `ip` `ipv6` `url` `email` `hash` `host name` | |
action_result.data.\*.tasks.\*.create_time | string | | 2025-07-30T12:57:16.516Z |
action_result.data.\*.tasks.\*.create_ts | numeric | | 1753880236516 |
action_result.data.\*.tasks.\*.end_time | string | | 2025-07-30T12:57:16.534Z |
action_result.data.\*.tasks.\*.end_ts | numeric | | 1753880236534 |
action_result.data.\*.tasks.\*.id | string | | 0059f4ae-ac28-45fa-8a77-7ac6067cc1f3 |
action_result.data.\*.tasks.\*.params.source | string | | urlhaus |
action_result.data.\*.tasks.\*.params.target | string | `ip` `ipv6` `url` `email` `hash` `host name` | google.com |
action_result.data.\*.tasks.\*.params.type | string | | host |
action_result.data.\*.tasks.\*.results | string | | |
action_result.data.\*.tasks.\*.rl | boolean | | True False |
action_result.data.\*.tasks.\*.start_time | string | | 2025-07-30T12:57:16.526Z |
action_result.data.\*.tasks.\*.start_ts | numeric | | 1753880236526 |
action_result.data.\*.tasks.\*.state | string | | completed |
action_result.data.\*.tasks.\*.status | string | | success |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get indicator intel lookup result'

Retrieve the result of a previously initiated Dossier lookup for an indicator (IP/URL/Host/MAC/Hash)

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | Specify the Job ID of the Dossier lookup job to retrieve the results for | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.job_id | string | | |
action_result.data.\*.results.\*.data | string | | |
action_result.data.\*.results.\*.data.info | string | | bad http status |
action_result.data.\*.results.\*.data.reason | string | | bad api response status code: 403 |
action_result.data.\*.results.\*.data.record_count | numeric | | 2 |
action_result.data.\*.results.\*.data.threat.\*.batch_id | string | | d1973fe0-3bc2-11f0-8f6b-4dbd30b8660e |
action_result.data.\*.results.\*.data.threat.\*.class | string | | APT |
action_result.data.\*.results.\*.data.threat.\*.detected | string | | 2025-05-20T12:35:31Z |
action_result.data.\*.results.\*.data.threat.\*.domain | string | | example.com |
action_result.data.\*.results.\*.data.threat.\*.email | string | | comments@example.com |
action_result.data.\*.results.\*.data.threat.\*.expiration | string | | 2026-05-06T14:00:00Z |
action_result.data.\*.results.\*.data.threat.\*.extended.comments | string | | THis is a sample email with a comment |
action_result.data.\*.results.\*.data.threat.\*.extended.notes | string | | THis is a sample email with a comment |
action_result.data.\*.results.\*.data.threat.\*.full_profile | string | | 001SAND30ab5807046:Netskope1 |
action_result.data.\*.results.\*.data.threat.\*.host | string | | example.com |
action_result.data.\*.results.\*.data.threat.\*.id | string | | d19ae961-3bc2-11f0-8f6b-4dbd30b8660e |
action_result.data.\*.results.\*.data.threat.\*.imported | string | | 2025-05-28T12:53:57.474Z |
action_result.data.\*.results.\*.data.threat.\*.profile | string | | 001SAND30ab5807046 |
action_result.data.\*.results.\*.data.threat.\*.property | string | | APT_EmdiviC2 |
action_result.data.\*.results.\*.data.threat.\*.received | string | | 2025-05-28T12:53:57.474Z |
action_result.data.\*.results.\*.data.threat.\*.threat_label | string | | Netskope CE | Comments |
action_result.data.\*.results.\*.data.threat.\*.threat_level | numeric | | 100 |
action_result.data.\*.results.\*.data.threat.\*.tld | string | | com |
action_result.data.\*.results.\*.data.threat.\*.type | string | | EMAIL |
action_result.data.\*.results.\*.data.threat.\*.up | string | | true |
action_result.data.\*.results.\*.params.source | string | | |
action_result.data.\*.results.\*.params.target | string | `ip` `ipv6` `url` `email` `hash` `host name` | |
action_result.data.\*.results.\*.params.type | string | | |
action_result.data.\*.results.\*.status | string | | |
action_result.data.\*.results.\*.time | numeric | | |
action_result.data.\*.results.\*.v | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'ip asset data lookup'

Look up asset data for a given IP address using IPAM address information

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_filter** | optional | Filter IP addresses by specific criteria (e.g., address=="192.168.1.100" or state=="USED") | string | |
**address_state** | optional | Filter by IP address state | string | |
**scope** | optional | Specify the scope for IP address lookup | string | |
**tag_filter** | optional | Filter IP addresses by specific tags (e.g. 'Tenable_scan'=='true') | string | |
**offset** | optional | Specify the offset from where to start pagination (default: 0) | numeric | |
**limit** | optional | Specify the maximum number of results to return (default: 100) | numeric | |
**order_by** | optional | Comma-separated JSON fields to sort the results. Use asc or desc for sorting direction. Defaults to ascending. Supports dot notation for nested fields (e.g. json_field_name asc|desc) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.address_state | string | | Used Free Any |
action_result.parameter.ip_filter | string | | address=="192.168.1.100" state=="USED" |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.offset | numeric | | 1 |
action_result.parameter.order_by | string | | |
action_result.parameter.scope | string | | global us-east |
action_result.parameter.tag_filter | string | | Rapid7_scan = True |
action_result.data.\*.results.\*.address | string | `ip` `ipv6` | |
action_result.data.\*.results.\*.dhcp_info | string | | |
action_result.data.\*.results.\*.discovery_attrs | string | | |
action_result.data.\*.results.\*.discovery_metadata | string | | |
action_result.data.\*.results.\*.external_keys | string | | |
action_result.data.\*.results.\*.host | string | `host name` | |
action_result.data.\*.results.\*.hwaddr | string | | |
action_result.data.\*.results.\*.id | string | | |
action_result.data.\*.results.\*.protocol | string | | |
action_result.data.\*.results.\*.state | string | | |
action_result.data.\*.results.\*.tags.Rapid7_scan_id | string | | 286 |
action_result.data.\*.results.\*.tags.Rapid7_scan_time | string | | 2025-07-18 10:37:07 |
action_result.data.\*.results.\*.tags.Snow_cmdb_table_name | string | | cmdb_ci_ip_device |
action_result.data.\*.results.\*.tags.Snow_sys_id | string | | 759b5756479212106f74bc8f016d43f0 |
action_result.data.\*.results.\*.updated_at | string | | |
action_result.data.\*.results.\*.usage | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get custom list'

Retrieve Custom Lists from Infoblox by ID, name, or filtering criteria

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**custom_list_id** | optional | Specify the ID of the custom list to retrieve | numeric | |
**name** | optional | The name of the custom list (name filtering can be only used in pairing with type) | string | |
**type** | optional | The type of the custom list | string | |
**tag_filter** | optional | Filter custom lists by specific tags (e.g: Test1=ss1) | string | |
**tag_sort_order** | optional | Sort custom list by Tags (e.g: Test1) | string | |
**offset** | optional | Specify the offset from where to start pagination | numeric | |
**limit** | optional | Specify the maximum number of results to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.custom_list_id | numeric | | |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.name | string | | |
action_result.parameter.offset | numeric | | 1 |
action_result.parameter.tag_filter | string | | |
action_result.parameter.tag_sort_order | string | | |
action_result.parameter.type | string | | |
action_result.data.\*.results.\*.confidence_level | string | | |
action_result.data.\*.results.\*.description | string | | |
action_result.data.\*.results.\*.id | numeric | | |
action_result.data.\*.results.\*.item_count | numeric | | |
action_result.data.\*.results.\*.items_described.\*.description | string | | |
action_result.data.\*.results.\*.items_described.\*.item | string | | 193.56.2.11/32 |
action_result.data.\*.results.\*.items_described.\*.status | string | | ACTIVE |
action_result.data.\*.results.\*.items_described.\*.status_details | string | | |
action_result.data.\*.results.\*.name | string | | |
action_result.data.\*.results.\*.threat_level | string | | |
action_result.summary.custom_list_id | numeric | | 834753 |
action_result.summary.name | string | | temp-custom |
action_result.summary.total_objects | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove custom list'

Delete a Custom List from Infoblox Cloud

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of the custom List to delete | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | numeric | | |
action_result.data | string | | |
action_result.summary.list_id | numeric | | |
action_result.summary.status | string | | deleted |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create network list'

Create a Network List with specified name, items, and optional description

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Specify the name of the network list | string | |
**items** | required | Specify the comma-separated items to include in the network list (e.g. 193.56.2.11/32,2001:db8:ffff:ffff:ffff:ffff:ffff:fff1/128) | string | |
**description** | optional | Specify a description for the network list | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | |
action_result.parameter.items | string | | 193.56.2.11/32 2001:db8:ffff:ffff:ffff:ffff:ffff:fff1/128 |
action_result.parameter.name | string | | |
action_result.data.\*.results.description | string | | |
action_result.data.\*.results.id | numeric | | |
action_result.data.\*.results.name | string | | |
action_result.data.\*.results.policy_id | numeric | | |
action_result.summary.description | string | | temporary desc |
action_result.summary.name | string | | test-network |
action_result.summary.network_list_id | numeric | | 1859146 |
action_result.summary.security_policy_id | numeric | | 204970 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update network list'

Update metadata and CIDRs of a specified network list

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_list_id** | required | Specify the ID of the network list to update | numeric | |
**name** | optional | Specify the name of the network list | string | |
**items** | optional | Specify the comma-separated items to include in the network list (e.g. 193.56.2.11/32,2001:db8:ffff:ffff:ffff:ffff:ffff:fff1/128) | string | |
**description** | optional | Specify a description for the network list (use 'empty' to clear the description) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | |
action_result.parameter.items | string | | 193.56.2.11/32 2001:db8:ffff:ffff:ffff:ffff:ffff:fff1/128 |
action_result.parameter.name | string | | |
action_result.parameter.network_list_id | numeric | | |
action_result.data.\*.results.description | string | | |
action_result.data.\*.results.id | numeric | | |
action_result.data.\*.results.name | string | | |
action_result.data.\*.results.policy_id | numeric | | |
action_result.summary.description | string | | update desc |
action_result.summary.name | string | | test update |
action_result.summary.network_list_id | numeric | | 1859146 |
action_result.summary.security_policy_id | numeric | | 204970 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get network list'

Retrieve network lists and their metadata

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_list_id** | optional | Specify the ID of a specific network list to retrieve. If provided, all other filter parameters will be ignored | numeric | |
**filter** | optional | Filter network lists by a logical expression string (e.g., name == 'net_list1'). Ignored if network_list_id is provided | string | |
**offset** | optional | Specify the offset from where to start pagination | numeric | |
**limit** | optional | Specify the maximum number of results to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.filter | string | | |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.network_list_id | numeric | | |
action_result.parameter.offset | numeric | | 1 |
action_result.data.\*.results.\*.created_time | string | | |
action_result.data.\*.results.\*.description | string | | |
action_result.data.\*.results.\*.id | numeric | | |
action_result.data.\*.results.\*.name | string | | |
action_result.data.\*.results.\*.policy_id | numeric | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get iq for td insights assets'

Retrieve the list of associated assets for a given Insight ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**insight_id** | required | ID of the insight to retrieve assets from | string | `infoblox insight id` |
**device_name** | optional | Filter assets by device or host name (case-insensitive partial match) | string | |
**indicators** | optional | Filter assets by comma-separated threat indicators (e.g. indicator1,indicator2) | string | |
**users** | optional | Filter assets by comma-separated user names (e.g. user1,user2) | string | `user name` |
**ip_address** | optional | Filter assets by comma-separated IP addresses | string | `ip` `ipv6` |
**is_verified** | optional | Filter by asset verification state: True (verified only) or False (unverified only); leave unselected to return both | string | |
**limit** | optional | Maximum number of results to return (default: 1000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.device_name | string | | DESKTOP-1234 |
action_result.parameter.indicators | string | | ikhwanschoolday.us |
action_result.parameter.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.parameter.ip_address | string | `ip` `ipv6` | 192.168.5.10 |
action_result.parameter.is_verified | string | | True False |
action_result.parameter.limit | numeric | | 1000 |
action_result.parameter.users | string | `user name` | john.doe |
action_result.data.\*.ip_address | string | `ip` `ipv6` | |
action_result.data.\*.mac_address | string | `mac address` | |
action_result.data.\*.device_name | string | | |
action_result.data.\*.is_verified | boolean | | |
action_result.data.\*.is_risky | boolean | | |
action_result.data.\*.total_events | numeric | | |
action_result.data.\*.indicators | string | | |
action_result.data.\*.users | string | `user name` | |
action_result.data.\*.description | string | | |
action_result.data.\*.locations | string | | |
action_result.data.\*.first_detected | string | | |
action_result.data.\*.last_detected | string | | |
action_result.summary.insight_id | string | | |
action_result.summary.total_assets | numeric | | |
action_result.summary.limit_applied | numeric | | |
action_result.message | string | | Successfully retrieved 1 insight asset(s) |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove network list'

Remove a specific network list by ID

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_list_id** | required | Specify the ID of the network list to delete | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.network_list_id | numeric | | |
action_result.data | string | | |
action_result.summary.network_list_id | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'host asset data lookup'

Look up host asset data using IPAM host information to retrieve detailed host information from Infoblox

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**host_filter** | optional | Filter IPAM hosts by specific criteria (e.g., name=="webserver01" or ip_address=="192.168.1.100") | string | |
**tag_filter** | optional | Filter IPAM hosts by specific tags (e.g. 'Tenable_scan'=='true') | string | |
**offset** | optional | Specify the offset from where to start pagination (default: 0) | numeric | |
**limit** | optional | Specify the maximum number of results to return (default: 100) | numeric | |
**order_by** | optional | Comma-separated JSON fields to sort the results. Use asc or desc for sorting direction. Defaults to ascending. Supports dot notation for nested fields (e.g. json_field_name asc|desc) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.host_filter | string | | |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.offset | numeric | | 1 |
action_result.parameter.order_by | string | | |
action_result.parameter.tag_filter | string | | |
action_result.data.\*.page | string | | |
action_result.data.\*.results.\*.addresses.\*.address | string | `ip` `ipv6` | |
action_result.data.\*.results.\*.addresses.\*.ref | string | | ipam/address/1a010fa0-617d-11f0-96d4-5a693772c4ec |
action_result.data.\*.results.\*.addresses.\*.space | string | | |
action_result.data.\*.results.\*.auto_generate_records | boolean | | True False |
action_result.data.\*.results.\*.comment | string | | |
action_result.data.\*.results.\*.created_at | string | | |
action_result.data.\*.results.\*.id | string | | |
action_result.data.\*.results.\*.name | string | | |
action_result.data.\*.results.\*.tags | string | | |
action_result.data.\*.results.\*.tags.Rapid7_scan | string | | true |
action_result.data.\*.results.\*.tags.Rapid7_scan_id | string | | 297 |
action_result.data.\*.results.\*.tags.Rapid7_scan_time | string | | 2025-07-21 09:32:57 |
action_result.data.\*.results.\*.tags.Rapid7_sync | string | | true |
action_result.data.\*.results.\*.updated_at | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'dns record lookup'

Perform a DNS record query to retrieve associated IPs or domains from Infoblox DDI

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**dns_record_filter** | optional | Filter DNS records by specific criteria (e.g., type=="PTR" and absolute_zone_name == "Test") | string | |
**tag_filter** | optional | Filter DNS records by specific tags (e.g., 'nios/federation_enabled'==true) | string | |
**offset** | optional | Specify the offset from where to start pagination (default: 0) | numeric | |
**limit** | optional | Specify the maximum number of results to return (default: 100) | numeric | |
**order_by** | optional | Comma-separated JSON fields to sort the results. Use asc or desc for sorting direction. Defaults to ascending. Supports dot notation for nested fields (e.g. json_field_name asc|desc) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.dns_record_filter | string | | |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.offset | numeric | | 1 |
action_result.parameter.order_by | string | | |
action_result.parameter.tag_filter | string | | |
action_result.data.\*.results.\*.absolute_name_spec | string | | |
action_result.data.\*.results.\*.disabled | boolean | | |
action_result.data.\*.results.\*.id | string | | |
action_result.data.\*.results.\*.inheritance_sources | string | | |
action_result.data.\*.results.\*.name_in_zone | string | | |
action_result.data.\*.results.\*.nios_metadata | string | | |
action_result.data.\*.results.\*.options | string | | |
action_result.data.\*.results.\*.provider_metadata | string | | |
action_result.data.\*.results.\*.rdata.address | string | `ip` `ipv6` | 192.168.10.101 |
action_result.data.\*.results.\*.ttl | numeric | | |
action_result.data.\*.results.\*.type | string | | |
action_result.data.\*.results.\*.updated_at | string | | |
action_result.data.\*.results.\*.view_name | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'dhcp lease lookup'

Perform a DHCP lease query to retrieve lease information from Infoblox DDI

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**dhcp_lease_filter** | optional | Filter DHCP leases by specific criteria (e.g., address == "127.0.0.1" and hostname == "ubuntu") | string | |
**offset** | optional | Specify the offset from where to start pagination (default: 0) | numeric | |
**limit** | optional | Specify the maximum number of results to return (default: 100) | numeric | |
**order_by** | optional | Comma-separated JSON fields to sort the results. Use asc or desc for sorting direction. Defaults to ascending. Supports dot notation for nested fields (e.g. json_field_name asc|desc) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.dhcp_lease_filter | string | | |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.offset | numeric | | 1 |
action_result.parameter.order_by | string | | |
action_result.data.\*.results.\*.address | string | `ip` `ipv6` | |
action_result.data.\*.results.\*.ends | string | | |
action_result.data.\*.results.\*.hardware | string | | |
action_result.data.\*.results.\*.hostname | string | | |
action_result.data.\*.results.\*.protocol | string | | |
action_result.data.\*.results.\*.space | string | | |
action_result.data.\*.results.\*.starts | string | | |
action_result.data.\*.results.\*.state | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'indicator threat lookup'

Lookup threat intelligence details for an indicator using Infoblox TIDE

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**indicator_type** | optional | Specify the type of indicator to search for | string | |
**limit** | optional | Maximum number of results to return (1-10000) | numeric | |
**indicator_value** | optional | Specify the indicator value based on the indicator type you want to search for | string | `ip` `ipv6` `url` `email` `hash` `host name` |
**domain** | optional | Specify the domain(s) to search for | string | |
**tld** | optional | Specify the top-level domain(s) to search for | string | |
**class** | optional | Specify the comma-separated threat class(es) to search for | string | |
**target** | optional | Specify target(s) to search for | string | |
**expiration** | optional | Period of time after which data is no longer considered active (YYYY-MM-DDThh:mm:ss.sssZ) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.class | string | | |
action_result.parameter.domain | string | | |
action_result.parameter.expiration | string | | |
action_result.parameter.indicator_type | string | | IP Host |
action_result.parameter.indicator_value | string | `ip` `ipv6` `url` `email` `hash` `host name` | |
action_result.parameter.limit | numeric | | 1 |
action_result.parameter.target | string | | |
action_result.parameter.tld | string | | |
action_result.data.\*.threat.\*.extended.original_profile | string | | IID:ANALYST |
action_result.data.\*.threat.\*.extended.protocol | string | | http |
action_result.data.\*.threat.\*.extended.references | string | | https://www.facebook.com/ads/library/?id=2061372931018687,https://www.virustotal.com/gui/file/447163012e9a41fdcca93e947b0ced12201547a13ecccd3efa2a07d0baa45cb2?nocache=1 |
action_result.data.\*.threat.\*.extended.sample_sha256 | string | | e6ae7a2081e7cd25ef9773fdd59344b9060286f88dae5f1e4168534dcc427e6b |
action_result.data.\*.threat.\*.hash_type | string | | SHA256 |
action_result.data.\*.threat.\*.threat_label | string | | IP IoC |
action_result.data.\*.threat.\*.up | string | | true |
action_result.summary.indicator_type | string | | All |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'create custom list'

Create a new custom list with specified details and items

Type: **contain** <br>
Read only: **False**

This action creates a new custom list in Infoblox Cloud using the Advanced Threat Control and Firewall (ATCFW) API. You can specify the list name, type, items (IPv4/IPv6 addresses or domain names), description, confidence level, threat level, and tags. The action validates input parameters and handles duplicate name errors appropriately.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Specify the name of the custom list to create | string | |
**type** | required | Specify the type of custom list to create | string | |
**items** | optional | Specify comma-separated items to include in the custom list (e.g. 193.56.2.11/32,2001:db8:ffff:ffff:ffff:ffff:ffff:fff1/128) | string | |
**description** | optional | Specify description of the custom list | string | |
**confidence_level** | optional | Specify the confidence level for the custom list | string | |
**threat_level** | optional | Specify the threat level for the custom list | string | |
**tags** | optional | Add tags to categorize and organize the custom list in JSON format. Example: {"environment":"production","team":"security"} | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.confidence_level | string | | HIGH MEDIUM LOW |
action_result.parameter.description | string | | Security blocklist for malicious domains |
action_result.parameter.items | string | | 192.168.1.1,example.com,2001:db8::1 |
action_result.parameter.name | string | | security_blocklist threat_indicators |
action_result.parameter.tags | string | | {"environment":"production","team":"security"} |
action_result.parameter.threat_level | string | | LOW MEDIUM HIGH INFO |
action_result.parameter.type | string | | custom_list |
action_result.data.\*.results.confidence_level | string | | LOW MEDIUM HIGH |
action_result.data.\*.results.description | string | | Custom List A Description Security blocklist for malicious domains |
action_result.data.\*.results.id | numeric | | 832628 451290 |
action_result.data.\*.results.item_count | numeric | | 3 15 0 |
action_result.data.\*.results.name | string | | custom_list_ad_1 security_blocklist |
action_result.data.\*.results.threat_level | string | | INFO LOW MEDIUM HIGH |
action_result.summary.custom_list_id | numeric | | 834753 |
action_result.summary.custom_list_name | string | | temp-custom |
action_result.summary.item_count | numeric | | 2 |
action_result.summary.total_objects | numeric | | 1 |
action_result.summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update custom list'

Update metadata of an existing custom list such as name, description, confidence level, threat level, or tags

Type: **generic** <br>
Read only: **False**

This action updates an existing custom list in Infoblox Threat Defense with DDI using the Advanced Threat Control and Firewall (ATCFW) API. You can update the list name, description, confidence level, threat level, and tags. Names must be unique among custom lists belonging to the same account.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**custom_list_id** | required | Specify the ID of the custom list to update | numeric | |
**name** | optional | Specify the new name of the custom list (must be unique) | string | |
**description** | optional | Specify the new description of the custom list | string | |
**confidence_level** | optional | Specify the confidence level for the custom list | string | |
**threat_level** | optional | Specify the threat level for the custom list | string | |
**tags** | optional | Add tags to categorize and organize the custom list (JSON format). Use 'empty' to clear existing tags | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.confidence_level | string | | HIGH |
action_result.parameter.custom_list_id | numeric | | 831224 |
action_result.parameter.description | string | | Updated description for the custom list |
action_result.parameter.name | string | | updated_custom_list |
action_result.parameter.tags | string | | {"category": "security", "severity": "high"} |
action_result.parameter.threat_level | string | | MEDIUM |
action_result.data.\*.results.confidence_level | string | | LOW MEDIUM HIGH |
action_result.data.\*.results.description | string | | Updated Custom List Description Updated security blocklist for malicious domains |
action_result.data.\*.results.id | numeric | | 831224 451290 |
action_result.data.\*.results.item_count | numeric | | 3 15 0 |
action_result.data.\*.results.name | string | | updated_custom_list security_blocklist_v2 |
action_result.data.\*.results.threat_level | string | | INFO LOW MEDIUM HIGH |
action_result.summary.custom_list_id | numeric | | 834753 |
action_result.summary.custom_list_name | string | | temp-custom |
action_result.summary.item_count | numeric | | 2 |
action_result.summary.total_objects | numeric | | 1 |
action_result.summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'remove security policy'

Remove a specific Security Policy by Security Policy ID

Type: **generic** <br>
Read only: **False**

This action permanently removes a security policy from Infoblox Cloud using the Advanced Threat Control and Firewall (ATCFW) API. The security policy will be deleted from the system and can no longer be used to enforce security rules. This action cannot be undone.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**security_policy_id** | required | Specify the ID of the security policy to delete | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.security_policy_id | numeric | | 12345 67890 |
action_result.data | string | | |
action_result.summary.security_policy_id | numeric | | 12345 |
action_result.message | string | | Successfully removed security policy with ID: 12345 |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get security policy'

Retrieve Security Policies and their metadata

Type: **investigate** <br>
Read only: **True**

This action retrieves Security Policies and their metadata from Infoblox Cloud using the Advanced Threat Control and Firewall (ATCFW) API. You can filter policies by name, description, tags, and other criteria.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**security_policy_filter** | optional | A logical expression string to filter security policies (e.g., name=='sec_policy_a') | string | |
**tag_filter** | optional | Filter security policy by specific tags | string | |
**tag_sort_filter** | optional | Sort security policy list by Tags | string | |
**offset** | optional | Specify the offset from where to start pagination | numeric | |
**limit** | optional | Specify the maximum number of results to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 100 |
action_result.parameter.offset | numeric | | 0 |
action_result.parameter.security_policy_filter | string | | name=='sec_policy_a' |
action_result.parameter.tag_filter | string | | |
action_result.parameter.tag_sort_filter | string | | |
action_result.data.\*.results.\*.default_action | string | | action_allow |
action_result.data.\*.results.\*.description | string | | Security Policy Description |
action_result.data.\*.results.\*.id | numeric | | 207665 |
action_result.data.\*.results.\*.migration_status.uses_legacy_feeds | boolean | | True False |
action_result.data.\*.results.\*.name | string | | CDS_Block |
action_result.data.\*.results.\*.rules.\*.description | string | | Suspicious destinations: Enables protection against hostnames |
action_result.data.\*.results.\*.scope_expr | string | | |
action_result.data.\*.results.\*.tags | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'create security policy'

Create a Security Policy, including its name, rules, associated network lists, DNS Forwarding Proxies (DFPs) etc

Type: **generic** <br>
Read only: **False**

This action creates a new Security Policy in Infoblox Cloud using the Advanced Threat Control and Firewall (ATCFW) API. The policy can include rules, network lists, DNS Forwarding Proxies, roaming device groups, and various configuration settings. The Security Policy name must be unique within the account.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Specify the name of the security policy to create | string | |
**description** | optional | Specify description for this security policy | string | |
**rules** | optional | Specify security rules as a list of JSON objects, each with action, type, data, policy_name and redirect_name | string | |
**network_lists** | optional | Specify the comma-separated network lists to associate with this policy (e.g 522436, 522438) | string | |
**dfps** | optional | Specify the comma-separated DNS Forwarding Proxies to associate with this policy (e.g 12456, 12458) | string | |
**roaming_device_groups** | optional | Specify the comma-separated Roaming Device Groups to associate with this policy (e.g 56312, 56316) | string | |
**block_dns_rebind_attack** | optional | Specify whether to block DNS rebinding attacks (true/false) | string | |
**safe_search** | optional | Specify whether to enable safe search filtering (true/false) | string | |
**tags** | optional | Add tags used to categorize and organize the Security Policy | string | |
**additional_parameters** | optional | JSON object containing additional parameters to update (precedence, access_codes, doh_enabled, doh_fqdn, ecs, onprem_resolve, dfp_services, net_address_dfps, user_groups, default_redirect_name) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | |
action_result.parameter.block_dns_rebind_attack | string | | true false |
action_result.parameter.description | string | | Security Policy A Description |
action_result.parameter.dfps | string | | 12456, 12458 |
action_result.parameter.name | string | | security_policy_a |
action_result.parameter.network_lists | string | | 522436, 522438 |
action_result.parameter.roaming_device_groups | string | | 56312, 56316 |
action_result.parameter.rules | string | | |
action_result.parameter.safe_search | string | | true false |
action_result.parameter.tags | string | | |
action_result.data.\*.results.default_action | string | | action_allow |
action_result.data.\*.results.description | string | | Security Policy A Description |
action_result.data.\*.results.id | numeric | | 226075 |
action_result.data.\*.results.migration_status.uses_legacy_feeds | boolean | | True False |
action_result.data.\*.results.name | string | | security_policy_a |
action_result.data.\*.results.rules.\*.description | string | | Suspicious destinations: Enables protection against hostnames that have not been directly linked to malicious behavior but behave in a manner that suggests malicious behavior may be imminent. |
action_result.data.\*.results.scope_expr | string | | |
action_result.data.\*.results.tags | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update custom list items'

Insert or remove individual items (e.g., IPs, domains) in a custom list

Type: **generic** <br>
Read only: **False**

This action allows you to insert or remove individual items from a custom list without replacing the entire list. You can add new items or remove existing items by specifying the action type and providing a comma-separated list of items. Duplicate items will be silently skipped during insertion operations.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**custom_list_id** | required | Specify the ID of the custom list to update | numeric | |
**action** | required | Insert or Delete custom List items | string | |
**items** | required | Specify comma-separated IPs and domains to add or remove from the custom list (e.g. 193.56.2.11/32,2001:db8:ffff:ffff:ffff:ffff:ffff:fff1/128) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action | string | | Add Remove |
action_result.parameter.custom_list_id | numeric | | 12345 |
action_result.parameter.items | string | | 193.56.2.11/32, example.com |
action_result.data.\*.deleted_items.\*.description | string | | |
action_result.data.\*.deleted_items.\*.item | string | | 193.56.2.11/32 |
action_result.data.\*.deleted_items.\*.status | numeric | | -1 |
action_result.data.\*.deleted_items.\*.status_details | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update security policy'

Update a specific Security Policy, including its name, rules, associated network lists, DNS Forwarding Proxies (DFPs) etc

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**security_policy_id** | required | Specify the ID of the security policy to update | numeric | |
**name** | optional | Specify the name of the security policy to update | string | |
**description** | optional | Specify an updated description for this security policy | string | |
**rules** | optional | Specify updated security rules as a list of JSON objects, each with action, type, data, policy_name and redirect_name | string | |
**network_lists** | optional | Specify the comma-separated network lists to associate with this policy (e.g 522436, 522438) | string | |
**dfps** | optional | Specify the comma-separated DNS Forwarding Proxies to associate with this policy (e.g 12456, 12458) | string | |
**roaming_device_groups** | optional | Specify the comma-separated Roaming Device Groups to associate with this policy (e.g 56312, 56316) | string | |
**block_dns_rebind_attack** | optional | Specify whether to block DNS rebinding attacks (true/false) | string | |
**safe_search** | optional | Specify whether to enable safe search filtering (true/false) | string | |
**tags** | optional | Update tags used to categorize and organize the Security Policy | string | |
**additional_parameters** | optional | JSON object containing additional parameters to update (precedence, access_codes, doh_enabled, doh_fqdn, ecs, onprem_resolve, dfp_services, net_address_dfps, user_groups, default_redirect_name) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | |
action_result.parameter.block_dns_rebind_attack | string | | |
action_result.parameter.description | string | | |
action_result.parameter.dfps | string | | 12456, 12458 |
action_result.parameter.name | string | | |
action_result.parameter.network_lists | string | | |
action_result.parameter.roaming_device_groups | string | | 56312, 56316 |
action_result.parameter.rules | string | | |
action_result.parameter.safe_search | string | | true false |
action_result.parameter.security_policy_id | numeric | | |
action_result.parameter.tags | string | | |
action_result.data.\*.results.default_action | string | | |
action_result.data.\*.results.description | string | | |
action_result.data.\*.results.id | numeric | | |
action_result.data.\*.results.migration_status.uses_legacy_feeds | boolean | | True False |
action_result.data.\*.results.name | string | | |
action_result.data.\*.results.rules.\*.description | string | | Suspicious destinations: Enables protection against hostnames |
action_result.data.\*.results.scope_expr | string | | |
action_result.data.\*.results.tags | string | | |
action_result.summary.default_action | string | | action_allow |
action_result.summary.description | string | | dscription |
action_result.summary.name | string | | temp-policy |
action_result.summary.policy_id | numeric | | 227005 |
action_result.summary.update_status | string | | Success |
action_result.summary.updated_time | string | | 2025-07-31T05:16:37Z |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get iq for td insights indicators'

Retrieve a filtered list of indicators associated with a specific Insight ID from Infoblox, supporting multiple filter parameters

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**insight_id** | required | ID of the insight to retrieve indicators from | string | `infoblox insight id` |
**indicators** | optional | Filter by comma-separated threat indicators (e.g. indicator1,indicator2) | string | |
**threat_level** | optional | Filter indicators by threat level (numeric value indicating severity) | string | |
**status** | optional | Filter by comma-separated indicator blocking status (e.g. Blocked,Not Blocked) | string | |
**users** | optional | Filter indicators by comma-separated user names | string | `user name` |
**detected_at** | optional | Return indicators detected on this RFC 3339 date (e.g. 2025-12-19T03:00:00Z); only records for that specific day are returned, not a range from this date to now | string | |
**limit** | optional | Specify the maximum number of results to return (default: 1000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.indicators | string | | ikhwanschoolday.us |
action_result.parameter.threat_level | string | | 3 |
action_result.parameter.status | string | | Not Blocked |
action_result.parameter.users | string | `user name` | john.doe |
action_result.parameter.detected_at | string | | 2025-12-19T03:00:00Z |
action_result.parameter.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.parameter.limit | numeric | | 1000 |
action_result.data.\*.indicators.\*.status | string | | Not Blocked |
action_result.data.\*.indicators.\*.threat_indicator | string | | ikhwanschoolday.us |
action_result.data.\*.indicators.\*.threat_level | numeric | | 3 |
action_result.data.\*.indicators.\*.confidence_level | numeric | | |
action_result.data.\*.indicators.\*.total_events | numeric | | |
action_result.data.\*.indicators.\*.threat_actors | string | | |
action_result.data.\*.indicators.\*.verified_assets | string | | |
action_result.data.\*.indicators.\*.unverified_assets | string | | |
action_result.data.\*.indicators.\*.users | string | `user name` | |
action_result.data.\*.indicators.\*.description | string | | |
action_result.data.\*.indicators.\*.detected_at | string | | |
action_result.data.\*.indicators.\*.first_detected | string | | |
action_result.data.\*.indicators.\*.last_detected | string | | |
action_result.summary.insight_id | string | | d00070a8-6ce9-40dd-8e2e-b8b7c05b303f |
action_result.summary.limit_applied | numeric | | 1 |
action_result.summary.total_indicators | numeric | | 1 |
action_result.message | string | | Successfully retrieved 1 insight indicator(s) |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get iq for td insights events'

Retrieve a detailed list of threat-related events for a specific Insight ID from Infoblox IQ for TD Insights

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**insight_id** | required | ID of the insight to retrieve events from | string | `infoblox insight id` |
**threat_level** | optional | Filter by threat level | string | |
**threat_confidence** | optional | Filter by threat confidence score | string | |
**indicator** | optional | Filter events by a specific threat indicator such as a domain, IP, or hash (e.g., hmdns.top) | string | |
**detected_from** | optional | Filter events detected on or after this RFC 3339 timestamp (e.g. 2025-12-19T03:00:00Z) | string | |
**detected_to** | optional | Filter events detected on or before this RFC 3339 timestamp (e.g. 2025-12-19T03:00:00Z) | string | |
**tclass** | optional | Filter by threat class category (e.g., Malware, Phishing, C2, Data Exfiltration) | string | |
**query** | optional | Filter by the DNS query name (the domain or hostname that was queried) | string | |
**device_ip** | optional | Filter events by comma-separated device IP addresses | string | `ip` `ipv6` |
**device_name** | optional | Filter by the name of the device that generated the event | string | |
**user** | optional | Filter events by comma-separated user names | string | `user name` |
**source** | optional | Filter events by the network source identifier where the DNS query originated | string | |
**limit** | optional | Specify the maximum number of results to return (default: 5000, max: 5000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.threat_confidence | string | | High |
action_result.parameter.device_ip | string | `ip` `ipv6` | 87.121.84.128 |
action_result.parameter.device_name | string | | DESKTOP-1234 |
action_result.parameter.detected_from | string | | 2025-12-19T03:00:00Z |
action_result.parameter.detected_to | string | | 2025-12-19T03:00:00Z |
action_result.parameter.indicator | string | | hmdns.top |
action_result.parameter.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.parameter.limit | numeric | | 5000 |
action_result.parameter.query | string | | aaa.hmdns.top. |
action_result.parameter.tclass | string | | EmergentDomain |
action_result.parameter.user | string | `user name` | john.doe |
action_result.parameter.source | string | | CREST_DFP (DFP) |
action_result.parameter.threat_level | string | | High |
action_result.data.\*.events.\*.action | string | | Block |
action_result.data.\*.events.\*.threat_confidence | string | | High |
action_result.data.\*.events.\*.device_country | string | | United States |
action_result.data.\*.events.\*.device_ip | string | `ip` `ipv6` | 87.121.84.128 |
action_result.data.\*.events.\*.device_name | string | | 87.121.84.128 |
action_result.data.\*.events.\*.mac_address | string | `mac address` | 64:c2:b3:d9:41:3d |
action_result.data.\*.events.\*.os_version | string | | Chrome OS |
action_result.data.\*.events.\*.policy | string | | Default Global Policy |
action_result.data.\*.events.\*.tfamily | string | | EmergentDomain |
action_result.data.\*.events.\*.tproperty | string | | |
action_result.data.\*.events.\*.tclass | string | | |
action_result.data.\*.events.\*.threat_level | string | | High |
action_result.data.\*.events.\*.detected_at | string | | |
action_result.data.\*.events.\*.query | string | | |
action_result.data.\*.events.\*.query_type | string | | |
action_result.data.\*.events.\*.user | string | `user name` | |
action_result.data.\*.events.\*.actor_name | string | | |
action_result.data.\*.events.\*.source | string | | |
action_result.data.\*.events.\*.indicator | string | | |
action_result.data.\*.events.\*.response | string | | |
action_result.data.\*.events.\*.dns_view | string | | |
action_result.data.\*.events.\*.feed | string | | |
action_result.data.\*.events.\*.dhcp_fingerprint | string | | |
action_result.data.\*.events.\*.response_region | string | | |
action_result.data.\*.events.\*.response_country | string | | |
action_result.data.\*.events.\*.device_region | string | | |
action_result.summary.insight_id | string | | 292GTP9s |
action_result.summary.total_events | numeric | | 48 |
action_result.summary.limit_applied | numeric | | 100 |
action_result.message | string | | Successfully retrieved 48 insight event(s) |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get iq for td insight details'

Retrieve the full detail view for a single IQ for TD Insight, including counts, severity, top indicators/assets, threat actors, and recommendations

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**insight_id** | required | ID of the insight to retrieve details for | string | `infoblox insight id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.data.\*.insight_id | string | `infoblox insight id` | |
action_result.data.\*.name | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.severity | string | | Critical High Medium Low |
action_result.data.\*.status | string | | |
action_result.data.\*.date_created | string | | |
action_result.data.\*.evaluation_start_date | string | | |
action_result.data.\*.evaluation_end_date | string | | |
action_result.data.\*.total_events | numeric | | |
action_result.data.\*.total_indicators | numeric | | |
action_result.data.\*.total_users | numeric | | |
action_result.data.\*.total_assets | numeric | | |
action_result.data.\*.total_verified_assets | numeric | | |
action_result.data.\*.total_unverified_assets | numeric | | |
action_result.data.\*.expiring_in_days | numeric | | |
action_result.data.\*.threat_properties | string | | |
action_result.data.\*.time_saved_seconds | numeric | | |
action_result.data.\*.top_indicators.\*.indicator | string | | |
action_result.data.\*.top_indicators.\*.description | string | | |
action_result.data.\*.top_indicators.\*.threat_actors.\*.id | string | | |
action_result.data.\*.top_indicators.\*.threat_actors.\*.name | string | | |
action_result.data.\*.top_assets.\*.asset | string | | |
action_result.data.\*.top_assets.\*.description | string | | |
action_result.data.\*.threat_actors.\*.actor_name | string | | |
action_result.data.\*.threat_actors.\*.actor_description | string | | |
action_result.data.\*.overview | string | | |
action_result.data.\*.key_recommendations.\*.id | string | `infoblox recommendation id` | b1c2d3e4-f5a6-7890-abcd-ef1234567890 |
action_result.data.\*.key_recommendations.\*.recommendation | string | | |
action_result.data.\*.key_recommendations.\*.type | string | | |
action_result.data.\*.key_recommendations.\*.action_taken | string | | |
action_result.summary.insight_id | string | | |
action_result.summary.status | string | | |
action_result.summary.severity | string | | |
action_result.summary.total_events | numeric | | |
action_result.summary.total_indicators | numeric | | |
action_result.summary.total_assets | numeric | | |
action_result.summary.total_users | numeric | | |
action_result.message | string | | Successfully retrieved details for insight ID: ea970c56-9d69-4844-8dc2-77d9be724c43 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update iq for td insight status'

Update the workflow status of a specific IQ for TD Insight, optionally recording an analyst comment describing the change

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**insight_id** | required | ID of the insight whose status should be updated | string | `infoblox insight id` |
**status** | required | New workflow status to assign to the insight | string | |
**comment** | optional | Optional analyst comment explaining the status change | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.parameter.status | string | | Resolved |
action_result.parameter.comment | string | | False positive - verified with user |
action_result.data.\*.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.data.\*.status | string | | Resolved |
action_result.data.\*.response | string | | {"success": "Status updated"} |
action_result.summary.insight_id | string | | |
action_result.summary.status | string | | |
action_result.message | string | | Successfully updated status to 'Resolved' for insight ID: ea970c56-9d69-4844-8dc2-77d9be724c43 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'execute iq for td recommendation action'

Execute a single recommendation action on an IQ for TD Insight, referencing the recommendation by the ID returned in the 'get iq for td insight details' action

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**insight_id** | required | Single ID of the insight whose recommendation is being actioned; comma-separated multiple values are not supported | string | `infoblox insight id` |
**recommendation_id** | required | Single ID of the recommendation to execute (from the 'key_recommendations' output of 'get iq for td insight details'); comma-separated multiple values are not supported | string | `infoblox recommendation id` |
**action** | optional | Optional override of the action verb applied to the recommendation (e.g. block, mark_risky, update_policy); when empty, the server picks the canonical verb for the recommendation type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.insight_id | string | `infoblox insight id` | ea970c56-9d69-4844-8dc2-77d9be724c43 |
action_result.parameter.recommendation_id | string | `infoblox recommendation id` | b1c2d3e4-f5a6-7890-abcd-ef1234567890 |
action_result.parameter.action | string | | block |
action_result.data.\*.results.\*.action | string | | block mark_risky update_policy |
action_result.data.\*.results.\*.status | string | | succeeded failed |
action_result.data.\*.results.\*.audit_entry_id | string | `infoblox audit entry id` | 3f8a1b2c-4d5e-6789-abcd-ef0123456789 |
action_result.data.\*.results.\*.reason | string | | applied already_applied action_failed resource_not_found invalid_request not_eligible |
action_result.data.\*.results.\*.message | string | | |
action_result.summary.insight_id | string | | |
action_result.summary.recommendation_id | string | `infoblox recommendation id` | |
action_result.summary.status | string | | succeeded failed |
action_result.message | string | | Successfully executed recommendation action for insight ID: ea970c56-9d69-4844-8dc2-77d9be724c43 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'undo iq for td recommendation action'

Reverse a previously executed recommendation action using the audit entry ID returned by the 'execute iq for td recommendation action' action

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**audit_entry_id** | required | Single audit log entry ID to undo (from the 'execute iq for td recommendation action' output); comma-separated multiple values are not supported | string | `infoblox audit entry id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.audit_entry_id | string | `infoblox audit entry id` | 3f8a1b2c-4d5e-6789-abcd-ef0123456789 |
action_result.data.\*.result.action | string | | allow undo_risky revert_policy |
action_result.data.\*.result.status | string | | succeeded failed |
action_result.summary.audit_entry_id | string | | |
action_result.summary.action | string | | |
action_result.summary.status | string | | |
action_result.message | string | | Successfully performed undo action 'allow' for audit entry ID: 3f8a1b2c-4d5e-6789-abcd-ef0123456789 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
