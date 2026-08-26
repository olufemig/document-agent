# Manufacturing Predictive Maintenance Service

```yaml
title: Manufacturing Predictive Maintenance Service
sector: Manufacturing
client_type: Food and beverage manufacturer
capabilities:
  - Internet of Things
  - Predictive maintenance
  - Machine learning
problem: Unplanned equipment downtime disrupted production schedules and maintenance teams relied on manual inspections.
solution: Built a sensor-data service that identified changing equipment conditions and prioritised maintenance investigations.
technologies:
  - AWS IoT Core
  - Python
  - Amazon SageMaker
  - Amazon Timestream
  - Grafana
outcomes:
  - Earlier visibility of equipment anomalies
  - More targeted maintenance planning
  - Improved production planning conversations
lessons:
  - Maintenance teams need clear reasons for every alert
  - Sensor quality checks are essential before model development
```

All content in this case study is fictional demonstration content.

The manufacturer collected machine telemetry but used it mainly for retrospective fault investigation. Maintenance teams had limited warning before failures affected production.

We combined sensor readings, maintenance records and production context into a monitored data service. The initial release focused on a small group of high-impact assets and gave engineers clear evidence behind each alert.

The service helped teams investigate developing issues earlier and plan interventions around production commitments. The work showed that useful maintenance analytics begins with reliable sensors and operationally meaningful alerts.
