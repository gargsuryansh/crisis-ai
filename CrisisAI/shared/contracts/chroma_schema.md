# ChromaDB Metadata Schema

> [!WARNING]
> **CRITICAL:** All metadata values in ChromaDB **MUST** be stored as strings. This includes coordinates (lat/lng) and confidence scores. This ensures compatibility and consistent indexing within ChromaDB.

## Collection Name
`incidents`

## ID Format
`incident_{md5hash}_{unix_timestamp}`

## Metadata Fields

| Field | Type | Allowed Values | Example |
|-------|------|----------------|---------|
| type | string | fire, flood, medical, earthquake, snakebite, accident, chemical, violence, unknown | "fire" |
| severity | string | LOW, MEDIUM, HIGH, CRITICAL | "HIGH" |
| area_name | string | City/Area name or "Unknown" | "Mumbai" |
| lat | string | Float as string | "19.076" |
| lng | string | Float as string | "72.877" |
| source | string | twitter, rss, mock, citizen_app | "twitter" |
| timestamp | string | ISO 8601 UTC | "2024-03-09T14:30:00Z" |
| status | string | open, responded, resolved | "open" |
| confidence | string | Float as string (0.0-1.0) | "0.87" |
