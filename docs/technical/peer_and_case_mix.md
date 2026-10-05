# Peer and Case-Mix Method

## Stage 2 audit and CSAT correction

Before peer analysis, the Stage 2 output was audited for grain, schemas, temporal roster context, and denominators. The ticket metrics contain 11,750 unique ticket IDs and roster context. The agent table reconciles to 44 distinct roster IDs. There are 5,196 populated valid 1–5 scores, of which 4,947 belong to resolved/closed tickets and 249 to open/pending tickets. The previous Stage 2 `valid_for_csat` and mean included all 5,196 scores, contrary to policy's survey-on-completion timing. Stage 2 now keeps `csat_response_flag` and the source score for all valid populated scores, but `valid_for_csat`, primary response count, mean, and score distribution include only resolved/closed tickets. The 249 anomalous scores are counted and flagged separately.

## Peer groups

Peers are assignment-specific, built from `agent_id`, effective team, tier, site, shift, and effective dates. Display names are never used. The hierarchy tries `tier + team + site + shift`, then `tier + team`, then `tier`. A level is supported by at least three distinct rostered agents, leaving at least two other-agent peers for leave-one-agent-out estimates. If even the tier cohort has fewer than three members, the context is unsupported. Tier is present at every level, so Tier 1 and Tier 2 cannot mix.

When one assignment falls back to a broader tier/team pool, it can use assignments in more specific child groups that share that broader context. Detailed-group agents continue to compare within their narrower cohort. This permits defensible small-group fallback without losing peers merely because their own group is more specific.

## Case mix

Assignment-level distributions report channel, priority, intake category, product family, team, tier, site, shift, and month/quarter. Shares include ticket denominators and explicit `(missing)` levels. These distributions are descriptive; differences do not establish causation.

The leave-one-agent-out standardization adjusts on channel, priority, calendar quarter, and product family within a tier-safe peer cohort. Priority is treated as the available routing-time context, although the source does not document whether agents can change it later. For each focal ticket, it estimates the peer outcome mean in the most specific supported cell, then broadens in this fixed order:

1. channel × priority × quarter × product family;
2. channel × priority × quarter;
3. channel × priority;
4. channel;
5. the selected peer cohort overall.

A cell needs at least five eligible peer tickets from at least two other agent IDs. Five is a configured support floor to avoid baselines from one or two observations, not a significance or quality threshold; cells below it fall back. Missing feature values form explicit matching levels. The outcome-specific peer baseline is the average of cell means weighted by the focal agent's eligible ticket mix. The focal agent's own tickets are excluded from every reference estimate. A period-specific comparison only uses peer observations from the same period; full-period comparisons are retrospective summaries, not forecasts.

Category is reported in mix tables but excluded from adjustment because the intake category may be re-tagged by an agent at closure. Transfers, handle time, SLA breach, refunds, replacements, resolution behavior, and agent notes are post-routing or outcome variables, so they are not adjustment predictors. Site and shift determine peer fallback context rather than being separately regressed.

## Outcomes and uncertainty

- CSAT is the completed-ticket mean on the 1–5 scale; open/pending populated scores remain anomaly flags and do not enter the primary outcome.
- Handle time is Stage 2 first-response-to-resolution minutes. All valid observations and outliers remain in the calculation.
- SLA outcome is the Stage 2 first-response breach indicator; `not_evaluable` tickets are outside its denominator.

Each adjusted row includes raw mean/rate, standardized peer expectation, observed-minus-expected gap, outcome eligibility count, peer sample and peer agent counts, adjustment coverage, and fallback level. Positive CSAT gaps indicate a higher score; positive handle-time/SLA gaps indicate a longer time or higher breach rate.

Intervals are approximate 95% normal intervals. Agent sampling variance and peer-cell mean variance are combined while treating the focal work mix as fixed. They assume independent tickets; reused peer cells and within-agent/period clustering induce dependence not represented in the interval, which can understate uncertainty. Intervals also do not account for peer-cell selection or unobserved case complexity. A `<30 eligible observations` evidence label is descriptive only, not a decision threshold. Single-observation intervals are undefined.

Quarterly stability compares the case-mix-adjusted gap's 95% interval overlap for outcomes with at least two peer-covered observations in at least two quarters. Labels are `variable_across_quarters`, `no_clear_shift_detected`, or `insufficient_period_evidence`; failure to detect a shift is not proof of stable performance. Monthly and quarterly adjusted outcome rows remain available for inspection.

## Limitations

This is an observational standardization, not a causal model. The selected factors are limited to fields available and considered plausibly pre-existing. Unrecorded issue severity, customer sentiment, and routing decisions may still differ. Sparse work cells use broader peer baselines, reducing adjustment specificity. Effective roster context is unavailable for open/pending tickets without a resolution time; these tickets remain in Stage 2 and are marked without a peer comparison in Stage 3. No ranking, bottom-ten list, composite score, or training recommendation is produced.
