## Grafana IRM Tooling

![Grafana IRM](https://grafana.com/media/docs/grafana-cloud/alerting-and-irm/grafana-cloud-docs-hero-alerts-irm.svg)

## Overview

[Grafana Incident Response Management (IRM)](https://grafana.com/docs/grafana-cloud/alerting-and-irm/) is a comprehensive solution for managing incidents and on-call schedules
within the Grafana ecosystem. This repo houses the code for tooling that can be used to for example migrate from other Incident Response Management providers to Grafana IRM.

## Repository Contents

### [Terraform Examples](./terraform/)

Examples and developer notes for managing Grafana IRM resources using the [Grafana Terraform provider](https://registry.terraform.io/providers/grafana/grafana/latest/docs). Includes sample configurations for schedules, escalation chains, routes, and more.

### [Migration Tools](./tools/migrators/)

Docker-based tools to migrate your existing on-call setup to Grafana IRM from:

- **PagerDuty** — schedules, escalation policies, services, notification rules, and event rulesets
- **Splunk OnCall (VictorOps)** — schedules, escalation policies, and paging policies
- **Opsgenie** — schedules, escalation policies, integrations, and notification rules

### [Utility Scripts](./tools/scripts/)

Python scripts for common IRM operations using the public API:

- Generate on-call hours and user reports
- Set up Mattermost/Discord webhook notifications
- Shift schedule management
- Create shift swap requests from Workday absences

### [Twilio Flows](./tools/twilio/)

Sample Twilio Studio flow configurations for voice-based alerting and routing.

## How to report issues?

Please create a post in the [Grafana Labs Community, IRM area](https://community.grafana.com/c/grafanacloud/grafana-irm/88).