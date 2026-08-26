# Telecom Network Assurance Modernisation

```yaml
title: Telecom Network Assurance Modernisation
sector: Telecommunications
client_type: Mobile network operator
capabilities:
  - Observability
  - Real-time analytics
  - Platform engineering
problem: Network operations teams used disconnected monitoring tools and struggled to correlate service degradation across systems.
solution: Implemented a unified observability platform for network events, service indicators and operational alerts.
technologies:
  - Kubernetes
  - Apache Kafka
  - OpenTelemetry
  - Elastic
  - Grafana
outcomes:
  - Faster correlation of related alerts
  - Improved visibility of service health
  - More consistent operational dashboards
lessons:
  - Alert quality matters more than alert volume
  - Shared service definitions improve incident handovers
```

All content in this case study is fictional demonstration content.

Operations teams had several monitoring products, each reporting a different part of network performance. During incidents, staff spent time joining alerts together before they could assess customer impact.

We introduced common telemetry conventions and a central event stream. Dashboards linked infrastructure signals to agreed service indicators, while alert rules were simplified with operations teams.

The platform made it easier to identify related issues and conduct clearer handovers between teams. The work demonstrated that observability improvements depend on common service definitions as much as tooling.
