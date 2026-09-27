**Unreleased**

* Migrated SOC Insights ingestion and actions to IQ for TD Insights, renaming the `get soc insights assets`/`indicators`/`events` actions and asset configuration parameters (`soc_*` to `iq_for_td_*`) to match Infoblox's updated terminology
* Added `get iq for td insight details`, `update iq for td insight status`, `execute iq for td recommendation action`, and `undo iq for td recommendation action` actions to view insight details/recommendations and drive the insight workflow directly from Splunk SOAR
* Removed the `get soc insights comments` action; use the `comment` parameter on `update iq for td insight status` to record analyst notes instead
* Added `x-Infoblox-client`/`x-Infoblox-customer` usage headers to outbound API calls, and fixed validation, error message, and datapath issues surfaced while auditing the migrated actions
* Validated and URL-encoded `insight_id` and `audit_entry_id` before interpolating them into IQ for TD Insights API paths, so caller input cannot traverse to sibling endpoints
