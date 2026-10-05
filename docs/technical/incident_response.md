# Incident Response Runbook

This runbook covers the dashboard and data bundle. The deployment owner must adapt contacts, paging routes, and retention to the actual environment; none are configured by this repository.

## Severity signals

- **Service unavailable:** container stopped/restarting, Streamlit health endpoint fails, or users cannot load the page.
- **Data integrity failure:** runtime health reports `unhealthy`, a required output/schema/hash is invalid, or the dashboard shows inconsistent/empty required data.
- **Degraded capability:** health reports `degraded` because optional AI diagnostics or Stage 7 evidence is absent. The deterministic dashboard remains available; current AI absence is expected.
- **Sensitive-data/security event:** suspected exposure of source/interim data, unauthorized access, leaked secret, or unexpected access to the dashboard.

## First response

1. Record UTC time, affected deployment, image digest, bundle release ID, and the exact health status. Do not copy ticket content, notes, agent identifiers, or secrets into the incident record.
2. Inspect container state, health output, and recent stdout/stderr logs (`docker inspect`, `docker logs --since 30m <container>`). Restrict log sharing to authorized responders.
3. For `unhealthy`, stop rollout or remove the instance from traffic. Check mount path/read-only status, release ID, manifest and integrity errors, and free disk/resources.
4. For service failure after a release, restore the last known-good image and its matching immutable bundle using the host platform rollback procedure.
5. For suspected exposure, restrict network access immediately, preserve relevant access/security logs, rotate affected credentials through the secret manager, and follow the organization security/privacy escalation process.
6. Record action, owner, outcome, and recovery time. Avoid editing an immutable release in place.

## Recovery and closeout

Rebuild only from trusted raw inputs in the isolated refresh flow. A bundle is eligible for activation only after pipeline, Stage 7, tests, image/container, and release gates pass. Preserve failed artifacts securely for diagnosis; remove/quarantine them under the organization retention policy. Close only after health and page access are restored, the active image/bundle pair is recorded, affected owners have been notified through approved channels, and a short root-cause/prevention note is complete.

There is no automatic alerting, central logging, backup service, or incident paging configured in this repository. Verify these capabilities with the deployment owner before production acceptance.
