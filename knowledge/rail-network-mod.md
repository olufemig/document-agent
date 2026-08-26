# 3. Rail Network Data Platform Modernisation

```yaml
title: Rail Network Data Platform Modernisation
sector: Rail
client_type: National rail operator
capabilities:
  - Data engineering
  - Cloud data platform
  - Real-time data
problem: Operational data was fragmented across legacy systems and difficult to combine.
solution: Built a cloud-based data platform integrating timetable, asset, disruption and passenger information.
technologies:
  - Azure
  - Databricks
  - Kafka
  - Delta Lake
  - Power BI
outcomes:
  - Faster access to operational data
  - Improved cross-system reporting
  - Better support for disruption analysis
lessons:
  - Shared data models reduce downstream complexity
  - Real-time use cases require strong data quality monitoring
```

All content in this case study is fictional demonstration content.

The operator had valuable operational information distributed across several platforms, each using different identifiers and data structures. Analysts spent significant time reconciling data before producing insight.

We designed a common ingestion layer and introduced a shared operational data model. Streaming feeds were combined with historical data to support both real-time monitoring and longer-term analysis.

The platform reduced manual reconciliation and made it easier to investigate disruption patterns. One of the strongest lessons was the value of resolving core identifiers early, particularly for services, stations and assets.

---
