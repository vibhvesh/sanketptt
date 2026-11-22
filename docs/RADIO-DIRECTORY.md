# Sanket Central Radio Directory

## Canonical source

The public radio station catalogue has one canonical, read-only public endpoint:

- JSON: `/data/radio-directory.json`
- Website browser: `/radio-directory/`
- Source generator: `scripts/refresh_radio_directory.py`
- Scheduled refresh: `.github/workflows/radio-directory.yml`

All public internet-radio experiences must read this same JSON endpoint. Do not maintain separate station lists inside Command Radio, Local Pulse, Soundwave, Newsroom, or Worldlink. Each experience may apply its own filters, ranking and presentation, but must not create a second catalogue.

Sanket PTT communication rooms are a separate security domain and must never be inserted into this public internet-radio directory.

## Schema version 4

Top-level fields:

- `schema_version`: integer schema version.
- `generated_at`: UTC ISO-8601 generation time.
- `directory_name`, `description`: catalogue identity and scope.
- `api.json`: canonical JSON endpoint.
- `sources`: source fetch counts and source errors from the last build.
- `station_count`, `country_count`, `countries`, `languages`, `regions`, `genres`: directory facets.
- `station_fields`: documented station record fields.
- `stations`: canonical station records.

Station identity is the stable `station_id` (same value as `id`). A stream URL is not a permanent identity and can change. Preserve both fields for backwards compatibility.

Station records expose `name`, `country`, `countrycode`, `region`, `city`, `languages` (also retained as legacy `language`), `categories` (also retained as legacy `type`), `tags`, `url`, `homepage`, `favicon`, `codec`, `bitrate`, `geo_lat`, `geo_long`, `source`, `directory_status`, and `last_checked`.

`directory_status: listed` means the station is present in a source directory. It does not mean that the stream was recently tested or is currently playable. `last_checked` remains null unless a future stream-health checker actually checks that station.

## Refresh and publishing

The GitHub Actions workflow refreshes the catalogue on its schedule and on manual dispatch. The generator merges public Radio Browser discovery records with the Akashvani public station list, deduplicates by stream URL, derives facets and writes the canonical JSON file. A changed JSON file is committed to the repository. The normal website deployment then publishes it.

Do not overwrite the JSON by hand as a routine update. Change the generator or its source mappings, then allow the workflow to rebuild the catalogue.

## Consumer contract

Consumers should:
1. Fetch `/data/radio-directory.json`.
2. Read `stations` and use `station_id` as the key.
3. Treat `languages` and `categories` as arrays; accept legacy `language` and `type` while older cached data exists.
4. Apply local product filters without modifying the canonical data.
5. Handle missing optional metadata and failed streams gracefully.

## Rights and privacy

This is a discovery index, not a relay or rebroadcast service. Listing a station does not grant rights to rebroadcast it. Public radio records must not contain private subscriber details, PTT rooms, credentials, or tenant-only metadata.
