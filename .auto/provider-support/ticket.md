# HTTP500 EngineCore error for Apertus-v1.5-70B native tool schema

Service: Inference Service
Endpoint: POST https://api.inference.cscs.ch/v1/chat/completions
Model: swiss-ai/Apertus-v1.5-70B

Could you inspect the serving-engine logs for an HTTP500 associated with the attached fictional request, and clarify whether the schema triggered an engine error or an unrelated transient failure?

## Incident

- Approximate client capture-file timestamp: 2026-10-15 04:10:39.185408 UTC. This is not a server timestamp.
- HTTP status: 500.
- Error type: InternalServerError.
- Message: "EngineCore encountered an issue. See stack trace (above) for the root cause."
- Request-body SHA256: 93690f08fb8605a84edce99a8875c2f96ab1aef033906597379d29015115eb55.
- Native OpenAI-style submit tool, forced tool choice, temperature0, max_tokens256, stream=false.
- candidate_ids is an array with min length implicit0, maxItems5, and items {"type":"string","enum":[]}.
- The requested arguments were {"label":1,"candidate_ids":[]}.

The exact canonical request body is attached as request.json. All input is fictional. No API key, Authorization header, personal data or benchmark answers are attached. error.json contains the captured error and HTTP status.

The request was not retried. The client stopped the comparison immediately and retained its failure records. We cannot determine usage for the failed request.

## Available controls, not proof of cause

The preceding six8B requests completed successfully, including the old empty-enum and specialized empty-array declarations. No70B specialized candidate request was sent after the500.

A later single known-good70B request, using a nonempty enum, returnedHTTP200 with valid arguments. Its approximate client capture-file timestamp is2026-10-15 04:16:43.216047 UTC. Thus70B was responding at that point, but this does not establish that enum[] caused the earlier error or prove a previously global outage recovered.

## Questions

1. What EngineCore exception occurred for the failed request? In particular, was an empty enum inside array items involved in schema compilation or constrained decoding?
2. Is this schema supported, intentionally rejected, or currently subject to a known limitation? If unsupported, should it return a validation4xx rather than an engine500?
3. Is a serving fix/version change needed before further testing? Please advise on safe reproduction rather than rerunning a possibly engine-breaking request against the shared endpoint.

No server implementation cause is asserted here. Provider logs are needed to distinguish schema-specific failure from a transient engine/resource problem.

Submission destination verified from the official inference documentation: https://support.cscs.ch
Documentation: https://docs.cscs.ch/services/inference/api/

Status: PREPARED, NOT SUBMITTED. This environment has no authenticated Service Desk submission session. Please submit through the Service Desk as an Inference Service incident and attach request.json and error.json from this directory.
