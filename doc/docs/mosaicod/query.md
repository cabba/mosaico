---
title: Query Engine
description: Deep semantic search capabilities.
sidebar:
    order: 5
---

Mosaico distinguishes itself from simple file stores with a powerful **Query Engine** capable of filtering data based on both high-level metadata and deep content values. Queries are submitted via the `query` action in the Control Layer using a structured, JSON-based syntax inspired by MongoDB.

## Scope of Search

The engine allows you to construct complex queries that span the entire data hierarchy simultaneously:

1.  **Platform Metadata:** Filter by structural attributes such as Sequence Name, Creation Date, or Status (Locked/Unlocked).
2.  **User Metadata:** Query the arbitrary JSON tags attached to sequences or topics (e.g., find sequences where `driver: "Alice"` AND `weather: "rainy"`).
3.  **Deep Content (Ontology):** Query the actual physical values recorded inside the sensor data.
    * *Example:* "Find all sequences where the GPS latitude is greater than 45.0".
    * **Mechanism:** This does not require opening and scanning terabytes of files. Instead, it relies on the **Statistical Indices** computed during the Ingestion phase. The engine checks the min/max bounds stored in the database for each chunk to rapidly include or exclude entire segments of data.

## Query Syntax

Queries are constructed as JSON objects that combine fields and operators.

```json
{
  "query": {
    "sequence.name": { "$regex": "test_run_*" },
    "user_metadata.driver": { "$eq": "Alice" },
    "data.imu.acceleration.x": { "$gt": 5.0 }
  }
}
```

## Response Structure
The query response is hierarchically grouped by Sequence. It provides not just the matching resource names, but the precise time windows where the condition was met.

```json
{
  "items": [
    {
      "sequence": "test_run_01",
      "topics": [
        { 
          "locator": "test_run_01/sensors/imu", 
          "timestamp_range": [1600000000, 1600005000] 
        }
      ]
    }
  ]
}
```