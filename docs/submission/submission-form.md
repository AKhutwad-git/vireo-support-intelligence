# Banao Technologies — Task 1 Submission Form

Responses below follow the actual questions included with the Task 1 brief. The local candidate currently promoted on port 8501 includes the Bottom 10 and Top 5 review queues, Q3 budget decision, numeric goal, and Product & Orders page. The linked [release record](release-record.md) describes the earlier `final-20261006-04` release; the current candidate and uncommitted source changes have not yet been recorded as a final clean-source release.

## What did you build, and what business outcome does it move? State the number and the money.

I built Vireo Support Intelligence, a deterministic support analytics and decision-support dashboard with optional AI diagnostics. It turns the request for a bottom-ten list into an evidence-gated training decision. For this dataset, **0 agents meet the configured threshold for a defensible training recommendation; all 44 agents remain monitored**. This avoids presenting unsupported personnel recommendations.

The analysis measured **₹3,253,060 contact exposure, ₹3,415,990 replacement exposure, and ₹5,350,871 refund exposure**. These are separate observed population exposure categories. They are not costs caused by agents, guaranteed savings, or an estimate of savings achievable through training. This evaluation establishes a baseline for future measurement but does not establish realized or causal financial benefit.

Proposed measurable business goal: reduce the resolver-associated first-response SLA breach rate by **1 percentage point**, from **9.06% (1,064/11,750)** to **8.06%** on a comparable ticket population. On the same observed denominator, the target corresponds to **117.5 fewer breach events** and a policy-credit sensitivity of **₹41,125** (`11,750 × 0.01 × ₹350 per breach`). The target is a proposed operational goal; the monetary figure is not causal, forecast, realized savings, or a guaranteed credit reduction.

## What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic. If you used no paid calls, say so.

The bounded real evaluation attempted **20 Gemini provider requests** on the 20 reviewed cases. Eight responses returned usage metadata: 4,581 input tokens, 1,483 output tokens, and 17,554 provider-reported total tokens. Twelve requests returned HTTP 429 and had no usage metadata. Billed cost and complete usage-based cost are **unknown** because pricing was not configured and the provider response did not report billed cost. No monthly AI cost is claimed; it would depend on the actual usage and applicable pricing plan. Vireo's volume is about **650 tickets/week × 52 ÷ 12 ≈ 2,817 tickets/month**. The 20-case evaluation is not a per-ticket production cost measurement, so multiplying it into a monthly spend would be unsupported.

This is not a cost estimate for a future AI-enabled configuration. Assistant/IDE subscription charges, engineering time, hosting, and other infrastructure costs were not measured here and are excluded.

## How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.

The supplied analysis covers **11,750 tickets and 44 agents**. Stage 7 passed **12 independent metric reconciliations** with zero difference against their reference calculations, **8 synthetic decision scenarios**, **220 explanation consistency checks**, and deterministic reproducibility checks. The current working-tree test run passed **135 tests, skipped 1, and failed 0**. The locally promoted candidate and the candidate preview use the same Docker image ID and read-only deployment bundle; this is local verification, not a clean-source or target-host acceptance.

There is no real-world agent-quality ground truth, so a real-world false-positive/false-negative rate or personnel-decision accuracy rate cannot be calculated. Synthetic scenarios test specified rule behavior; they are not a substitute for that ground truth. Separately, the bounded AI evaluation produced **3 schema-valid predictions out of 20 attempted cases**, and all 3 matched their human labels. The other 17 cases had no valid prediction: 5 failed schema validation and 12 received HTTP 429. The 3/3 agreement is conditional on valid predictions and is **not overall model accuracy**; this run is too incomplete to establish model accuracy/error rate over the evaluation set. The prompt contract was tightened afterward and has not been evaluated live. Known difficult cases include agents with small or mixed evidence, approximate intervals that assume independent tickets, and tickets without effective roster context. The deterministic evidence gate responds conservatively: it recommends no agents for training in this dataset.

## Did you change, narrow, or push back on the client's ask? What, when, and why?

Yes. The initial request asked for a bottom-ten ranking. During analysis I changed the decision approach from simple ranking to evidence-gated, Tier-safe peer comparison because the supplied policy indicates that differences in tier, team, and queue assignment can confound agent comparisons. The product now shows a **Bottom 10 — Review Queue** and **Top 5 — Bonus Review** based on a transparent composite of peer-adjusted point estimates. They are management review lists, not retraining or bonus decisions. Point-estimate candidates were retained only as exploratory sensitivity analysis for the training decision. Since the uncertainty evidence did not support a defensible training ranking, the product still reports **0 defensible training candidates and 44 monitored agents**.

## What is wrong with what you are handing us? Be specific: bugs, shortcuts, things you know are off.

Known limitations and shortcuts:

- Stage 3 uncertainty intervals are approximate and assume independent tickets; clustered case-mix uncertainty is incomplete.
- There is no real-world ground truth for agent-quality false-positive/false-negative rates and no genuine out-of-time validation.
- Stage 5 has a limited real evaluation but no defensible overall model-quality estimate or complete cost measurement: only 3/20 cases produced schema-valid predictions, with 5 schema failures and 12 HTTP 429 responses. The 3/3 label agreement is not overall accuracy. The revised prompt has not been evaluated live.
- 567 tickets lack effective roster context and are retained without peer comparison.
- Valid handle-time outliers are retained; elapsed resolution time is not paid labor time.
- `agent_id` identifies the resolver, not necessarily the first responder, so SLA results are resolver-associated.
- Source timestamp provenance, text-quality detection gaps, and ambiguous source relationships are documented in the forensic findings.

These are known analytical or evidence limitations, not claims that the application is free of all bugs. Stage 7 remains **VALIDATED WITH MATERIAL LIMITATIONS**.

## What did you deliberately leave out, and why that rather than something else?

I left out a bottom-ten retraining recommendation unsupported by the evidence, a bonus decision, full-corpus AI inference, causal attribution of costs to agents, and a claimed savings/ROI figure. A bounded 20-request Gemini evaluation was run; its limited coverage does not support an overall model-quality claim. With 0 evidence-gated training candidates, the Q3 budget decision is **₹0 allocated to agent-specific retraining; reserve ₹4,00,000 pending stronger evidence or targeted process investigation**. These choices avoid implying more certainty than the available data supports. External hosting and centralized monitoring/paging are also not configured or verified in this evaluation release.

## Anything you built or found that nobody asked for?

The work includes data-quality and source reconciliation checks, Tier-safe peer and case-mix comparisons, an observed economics view, and synthetic decision-rule validation. These provide context and checks for the requested agent metrics and training decision; none establishes agent causality or guaranteed savings.

## What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.

ChatGPT was used extensively for architecture review, analytical reasoning, debugging, documentation, test planning, release review, and prompt generation. An IDE coding assistant was also used to implement and modify repository files. The specific model names used across those assistant sessions were not reliably recorded, so I cannot identify them accurately. Separately, the Vireo AI evaluation used Google Gemini 2.5 Flash through the OpenAI-compatible endpoint for 20 requests on the reviewed fixture. Three outputs passed schema validation and matched their labels; 5 failed schema validation and 12 returned HTTP 429. This is limited evaluation evidence, not overall model accuracy or production readiness.

AI assistance helped with implementation and review. Specific instances of time wasted on AI assistance were not tracked, so I cannot quantify or attribute them reliably. I kept AI optional rather than making per-ticket model calls across the full corpus. Point-estimate-only candidates were discarded as recommendations and kept only as exploratory sensitivity results because the evidence gate did not support action. Earlier stale release evidence/documentation was corrected before the final release. No live model result is represented as validated evidence.

Provider/API billed cost for the evaluation: **unknown**. Usage was reported for 8 responses, but pricing was not configured and billed cost was not available. Assistant/IDE subscription cost was not tracked or attributed to this project.

Three-minute screen recording: [Watch the recording](https://drive.google.com/file/d/18ZwQtc7AO3cQEUVh60FQo6zapPqsg9kT/view?usp=sharing).

## Your Public Google Drive Link

Submission folder: [Open the Google Drive folder](https://drive.google.com/drive/folders/1K7uAWSHZvTuWjK92iHemTx96dDmztH6x?usp=sharing). Link supplied by the submitter; access permissions were not independently verified.

## Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. The raw source pack is supplied separately and is not committed to Git. Place it in `data/raw/` as described in the README before running the pipeline.
2. Rebuild and validate from the locked environment using the README commands. A fresh checkout does not contain the ignored local release bundle; use a new unique release ID and keep the verified image and bundle paired.
3. Keep review and action separate: the Bottom 10 and Top 5 are review queues only; Stage 6 still gives **0 defensible training candidates / 44 monitored agents**, and the Q3 training budget remains reserved. The bounded AI evaluation had only 3 valid predictions among 20 cases and cannot support an overall accuracy claim; Stage 7 has material limitations.

## Honest hours spent. One number.

Approximately **20 hours**. This is an honest retrospective estimate, not time tracked with a timer.

## Github Repo Link — Please upload your Github Repo URL (Public)

[https://github.com/AKhutwad-git/vireo-support-intelligence](https://github.com/AKhutwad-git/vireo-support-intelligence)

This is the repository URL supplied by the submitter and matches the configured Git remote. The repository page was reachable and labeled **Public** when checked on 2026-10-07. Recording and Drive link access were not independently verified.

At this audit, the remote `main` still points to `47d3b1c`; the current candidate implementation and documentation changes are uncommitted locally and are not yet on GitHub. Do not treat the public URL as containing this candidate until the final changes are committed and pushed.
