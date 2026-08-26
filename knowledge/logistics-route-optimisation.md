# Logistics Route Optimisation Service

```yaml
title: Logistics Route Optimisation Service
sector: Logistics
client_type: Regional distribution company
capabilities:
  - Optimisation
  - Operations research
  - Data integration
problem: Daily delivery routes were planned manually, making it difficult to respond to changing orders, driver constraints and depot capacity.
solution: Developed an optimisation service that proposed feasible delivery plans for planners to review and adjust.
technologies:
  - Python
  - Google OR-Tools
  - PostgreSQL
  - Docker
  - Mapbox
outcomes:
  - More consistent route-planning baseline
  - Faster response to daily changes
  - Better visibility of capacity constraints
lessons:
  - Planners need the ability to explain and adjust recommendations
  - Operational constraints must be modelled before route distance is optimised
```

All content in this case study is fictional demonstration content.

Dispatchers relied on local knowledge to create routes, which worked well for familiar patterns but was difficult to scale when order volumes changed.

We captured delivery windows, vehicle limits, driver constraints and depot rules in a planning model. The service produced recommended routes with clear constraint warnings, leaving dispatchers in control of the final plan.

Planning teams gained a consistent starting point for each day while retaining the flexibility needed for real-world exceptions. The key lesson was that the shortest route is not always the most practical plan.
