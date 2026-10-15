# Provider availability check after owner approval

The owner said 'go' after the request to investigate the provider failure. One known-good fictional70B request was sent, not a resumed benchmark or a replay of the failing empty-enum declaration.

Result: HTTP200, matching model identity, valid complete arguments, exact requested tuple, known124 input/17 output tokens (141 total). Observed wall1.5557322518434376 seconds. No retries. The request used the previously successful simple schema with two nonempty enum choices, not an empty enum. No application or benchmark changes occurred.

Artifacts: output/cscs/provider-health-check-1792037801819377479/{request,capture,completed}.json. No credential headers were stored. The health check is an operational diagnostic, not a new optimization metric or NLI quality result.

## What is established

The70B endpoint currently responds successfully to a known-good request. A persistent all-request70B outage is not supported by this observation. It does not prove recovery from a previously global outage: the earlier failure may have been specific to its schema or transient.

The original failed request remains HTTP500 on the old-native empty-candidate declaration. Its capture file modification time is approximately2026-10-15T04:10:39.185408+00:00; this is a client-side file timestamp, not a server event timestamp. Model: swiss-ai/Apertus-v1.5-70B. Provider error: 'EngineCore encountered an issue. See stack trace (above) for the root cause.'

Remaining explanations include empty-enum compilation/generation failure, a transient engine/resource error, or another request-specific backend failure. The successful health check cannot distinguish them. No claim that enum[] caused the crash is justified without provider logs or a safe server-side reproduction.

## Preserved boundary and next evidence

The stopped experiment's STOP.json and inflight.json remain, completed.json is absent, and no remaining planned calls were sent. Its primary and full usage remain unavailable. The failing request was not resubmitted, and the missing70B candidate was not sent under a different identity.

Provider-side EngineCore logs around the above timestamp, or a provider-confirmed explanation/fix, are needed to determine the cause. The original failing payload is entirely fictional and can be supplied from output/cscs/provider-schema-empty-source-v1/06-request.json without credentials. Do not send credential files or Authorization headers. Do not run this payload against the shared endpoint again merely to obtain a cleaner comparison.
