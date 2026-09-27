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
