# Banao Technologies — Task 1 Submission Form

Responses below follow the actual questions included with the Task 1 brief. Results refer to the verified release recorded in [release-record.md](release-record.md).

## What did you build, and what business outcome does it move? State the number and the money.

I built Vireo Support Intelligence, a deterministic support analytics and decision-support dashboard with optional AI diagnostics. It turns the request for a bottom-ten list into an evidence-gated training decision. For this dataset, **0 agents meet the configured threshold for a defensible training recommendation; all 44 agents remain monitored**. This avoids presenting unsupported personnel recommendations.

The analysis measured **₹3,253,060 contact exposure, ₹3,415,990 replacement exposure, and ₹5,350,871 refund exposure**. These are separate observed population exposure categories. They are not costs caused by agents, guaranteed savings, or an estimate of savings achievable through training. This evaluation establishes a baseline for future measurement but does not establish realized or causal financial benefit.

## What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic. If you used no paid calls, say so.

The final evaluation run made **0 AI provider/API requests**, so paid provider/API cost for that run was **₹0**. At the stated volume, approximately `650 tickets/week × 52 weeks ÷ 12 months = 2,817 tickets/month`. With the tested AI-disabled configuration, `0 provider calls/week × 52 ÷ 12 = 0 provider calls/month`, so paid provider/API usage remains **₹0/month** under that same configuration.

This is not a cost estimate for a future AI-enabled configuration. Assistant/IDE subscription charges, engineering time, hosting, and other infrastructure costs were not measured here and are excluded.

## How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.

The supplied analysis covers **11,750 tickets and 44 agents**. Stage 7 passed **12 independent metric reconciliations** with zero difference against their reference calculations, **8 synthetic decision scenarios**, **220 explanation consistency checks**, and deterministic reproducibility checks. The full test suite reported **119 passed, 1 skipped, 0 failed**.

There is no real-world agent-quality ground truth, so a real-world false-positive/false-negative rate or personnel-decision accuracy rate cannot be calculated. Synthetic scenarios test specified rule behavior; they are not a substitute for that ground truth. Known difficult cases include agents with small or mixed evidence, approximate intervals that assume independent tickets, and tickets without effective roster context. The default evidence gate responds conservatively: it recommends no agents for training in this dataset.

## Did you change, narrow, or push back on the client's ask? What, when, and why?

Yes. The initial request asked for a bottom-ten ranking. During analysis I changed the decision approach from simple ranking to evidence-gated, Tier-safe peer comparison because the supplied policy indicates that differences in tier, team, and queue assignment can confound agent comparisons. Point-estimate candidates were retained only as exploratory sensitivity analysis. Since the uncertainty evidence did not support a defensible ranking, the final product reports **0 defensible training candidates and 44 monitored agents**, rather than manufacturing a bottom-ten recommendation.

## What is wrong with what you are handing us? Be specific: bugs, shortcuts, things you know are off.

Known limitations and shortcuts:

- Stage 3 uncertainty intervals are approximate and assume independent tickets; clustered case-mix uncertainty is incomplete.
- There is no real-world ground truth for agent-quality false-positive/false-negative rates and no genuine out-of-time validation.
- Stage 5 has no real model predictions, model-quality evaluation, or real model usage-cost measurement. AI was unavailable in the final evaluation run.
- 567 tickets lack effective roster context and are retained without peer comparison.
- Valid handle-time outliers are retained; elapsed resolution time is not paid labor time.
- `agent_id` identifies the resolver, not necessarily the first responder, so SLA results are resolver-associated.
- Source timestamp provenance, text-quality detection gaps, and ambiguous source relationships are documented in the forensic findings.

These are known analytical or evidence limitations, not claims that the application is free of all bugs. Stage 7 remains **VALIDATED WITH MATERIAL LIMITATIONS**.

## What did you deliberately leave out, and why that rather than something else?

I left out a bottom-ten recommendation unsupported by the evidence, live AI provider calls in the final run, causal attribution of costs to agents, and a claimed savings/ROI figure. These would imply more certainty than the available data supports. I kept the deterministic metrics and decision gate authoritative, surfaced observed economics as context, and documented the remaining uncertainty. External hosting and centralized monitoring/paging are also not configured or verified in this evaluation release.

## Anything you built or found that nobody asked for?

The work includes data-quality and source reconciliation checks, Tier-safe peer and case-mix comparisons, an observed economics view, and synthetic decision-rule validation. These provide context and checks for the requested agent metrics and training decision; none establishes agent causality or guaranteed savings.

## What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.

ChatGPT was used extensively for architecture review, analytical reasoning, debugging, documentation, test planning, release review, and prompt generation. An IDE coding assistant was also used to implement and modify repository files. The specific model names used across those assistant sessions were not reliably recorded, so I cannot identify them accurately. The submitted Vireo application made no live AI provider calls in the final evaluation run; Stage 5 was unavailable and produced no real predictions.

AI assistance helped with implementation and review. Specific instances of time wasted on AI assistance were not tracked, so I cannot quantify or attribute them reliably. I kept AI optional rather than making per-ticket model calls across the full corpus. Point-estimate-only candidates were discarded as recommendations and kept only as exploratory sensitivity results because the evidence gate did not support action. Earlier stale release evidence/documentation was corrected before the final release. No live model result is represented as validated evidence.

Provider/API cost in the final evaluation run: **₹0**, because there were zero provider requests. Assistant/IDE subscription cost was not tracked or attributed to this project.

Three-minute screen recording: [Watch the recording](https://drive.google.com/file/d/18ZwQtc7AO3cQEUVh60FQo6zapPqsg9kT/view?usp=sharing).

## Your Public Google Drive Link

Submission folder: [Open the Google Drive folder](https://drive.google.com/drive/folders/1K7uAWSHZvTuWjK92iHemTx96dDmztH6x?usp=sharing). Link supplied by the submitter; access permissions were not independently verified.

## Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. The raw source pack is supplied separately and is not committed to Git. Place it in `data/raw/` as described in the README before running the pipeline.
2. Rebuild and validate from the locked environment using the README commands. A fresh checkout does not contain the ignored local release bundle; use a new unique release ID and keep the verified image and bundle paired.
3. Preserve the evidence-gated result: **0 defensible training candidates; 44 monitored agents**. Stage 5 AI is unavailable in the verified run, Stage 7 has material limitations, and the point-estimate-only names are exploratory, not recommendations.

## Honest hours spent. One number.

Approximately **20 hours**. This is an honest retrospective estimate, not time tracked with a timer.

## Github Repo Link — Please upload your Github Repo URL (Public)

[https://github.com/AKhutwad-git/vireo-support-intelligence](https://github.com/AKhutwad-git/vireo-support-intelligence)

This is the repository URL supplied by the submitter and matches the configured Git remote. Public accessibility was not independently verified.
