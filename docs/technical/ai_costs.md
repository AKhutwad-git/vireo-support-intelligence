# Stage 5 AI Cost Controls and Estimates

## Current configuration and observed run

The provider is disabled by default (`ai.enabled: false`), model is `unset`, and no API key is required. The pipeline selected at most 250 tickets from a deterministic candidate pool of 6,516; it analyzed **0**, made **0** provider calls, served **0** results from cache, and skipped the other 11,500 tickets (5,234 had no enabled signal or eligible text; 6,266 eligible candidates were excluded by the top-N cap). No external customer text was sent.

For those 250 selected candidates, the prompt-size proxy estimated 144,314 input tokens and configured maximum-response allowance of 45,000 output tokens if analyzed. This proxy uses UTF-8 character count divided by four and is not provider-tokenizer usage. The pipeline made zero provider requests, so estimated run cost is $0 for this run; the estimated cost if the selected sample were analyzed and cost per analyzed ticket remain unavailable because no model price is configured. Actual token usage/billing is unavailable.

## Pricing configuration

Set `ai.pricing.input_per_million_usd`, `output_per_million_usd`, `currency`, and `source` in `configs/config.yaml` using the selected provider's current published or contracted rates. No pricing has been inserted by this implementation. If usage is returned by the provider, the report stores actual input/output token counts and an estimate using these configured rates; that estimate is not a provider invoice.

## Cache and selection impact

The SHA-256 key includes prompt text, model ID, and prompt version. Valid outputs are reused without another call; raw conversations are not cached. Selection is deterministic and limited to at most 250 tickets per pipeline run by default. Cache impact is currently zero because there has been no configured provider run.

## Monthly projection

At 650 tickets/week × 4.333 weeks/month, the planning volume is about 2,816 tickets/month. The observed candidate rate was 6,516/11,750 (55.46%), giving an uncapped targeted projection of about **1,562 candidate analyses/month**. Full analysis is a separate hypothetical of 2,816 tickets/month. The prompt-size proxy projects about 902k input + 281k output tokens for targeted analysis and 1.626m input + 507k output tokens for full analysis; these estimates are in `ai_run_report.json`. Dollar projections remain null until pricing is configured. The targeted projection is extrapolated from this dataset and does not apply the per-run cap across hypothetical multiple monthly runs. Targeted analysis is the recommended operating design; full analysis is shown only for comparison.
