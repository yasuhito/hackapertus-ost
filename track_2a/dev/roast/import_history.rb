# Offline import: verifies raw events, never starts a provider/model.
require "json"
require "digest"
require "fileutils"
require_relative "measurement"
source, output = ARGV
abort "usage: import_history.rb SOURCE OUTPUT" unless source && output
FileUtils.mkdir_p(output)
manifest = JSON.parse(File.read("#{source}/manifest.json"))
records = Dir["#{source}/calls/*/success.json"].sort.map do |file|
  meta = JSON.parse(File.read(file)); folder = File.dirname(file)
  event_files = Dir["#{folder}/attempt-*-events.jsonl"].sort
  events = event_files.flat_map { |path| File.readlines(path).reject { |l| l.strip.empty? }.map { |line| JSON.parse(line) } }
  terminal = events.reverse.find { |event| event["type"] == "turn.completed" }
  raise "usage/event mismatch: #{folder}" unless terminal && terminal["usage"] == meta["usage"]
  {
    "run_id" => "imported-dev54", "case_id" => meta.fetch("id"), "attempt_id" => "legacy:#{File.basename(folder)}:1",
    "config" => meta.fetch("variant"), "kind" => "model_attempt", "model" => meta.fetch("model"), "effort" => meta.fetch("effort"),
    "usage" => OstEval::Usage.read("codex_cli", terminal["usage"]), "source_events" => event_files,
    "source_event_hashes" => event_files.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
    "prompt_sha256" => meta["prompt_sha256"], "historical_commit" => nil, "historical_dirty_diff_sha256" => nil,
    "historical_source_hashes" => manifest["code_hashes"], "data_sha256" => manifest["sample_sha256"],
    "provider_version" => "Codex CLI 0.160.0", "api_wait_ms" => nil, "cli_subprocess_wall_ms" => meta["call_wall_ms"],
    "selection_ms" => meta["selection_ms"], "estimated_context_tokens_utf8_bytes_div4" => meta["context_proxy_tokens"],
    "request_sent" => true, "new_request_on_import" => false, "usage_origin" => "raw turn.completed event"
  }
end
raise "expected 81 unique model records" unless records.size == 81 && records.map { |r| r['attempt_id'] }.uniq.size == 81
setup = { "run_id" => "imported-dev54", "case_id" => nil, "attempt_id" => "legacy:setup-before-send:1", "kind" => "setup_failure", "request_sent" => false,
          "usage" => OstEval::Usage.read("codex_cli", nil), "new_request_on_import" => false }
partitions = { "A_full" => records.select { |r| r['config'] == 'baseline' && r['case_id'].end_with?('-A') },
               "A_selected" => records.select { |r| r['config'] == 'vote_pages' },
               "B_shared_once" => records.select { |r| r['case_id'].end_with?('-B') } }
summary = {
  "model_attempts" => records.size, "setup_attempts" => 1, "total_attempt_records" => records.size + 1, "new_model_calls" => 0,
  "model_attempts_usage" => OstEval::Usage.aggregate(records), "all_attempts_usage" => OstEval::Usage.aggregate(records + [setup]),
  "partitions" => partitions.transform_values { |r| { "n" => r.size, "usage" => OstEval::Usage.aggregate(r),
    "context_estimate_total" => r.sum { |x| x['estimated_context_tokens_utf8_bytes_div4'] || 0 } } },
  "cache_semantics" => "Codex copies input_tokens directly from Responses usage; cached/cache-write are subsets. Pi subtracts cached/cache-write from fresh input, so normalize by adding them back once.",
  "output_semantics" => "Output already includes reasoning. Do not add reasoning to output or total.",
  "semantics_sources" => ["https://github.com/openai/codex/blob/main/codex-rs/codex-api/src/sse/responses.rs#L121-L135", "Pi 1.1.0 installed pi-ai/dist/api/openai-responses-shared.js lines441-451 and types.d.ts Usage"],
  "organizer_proxy_measured" => false, "official_score" => nil,
  "timing_note" => "API-only wait was not captured historically. CLI subprocess wall time includes startup/transport/streaming, and is not official non-LLM time.",
  "missing_provenance" => ["historical commit and dirty diff were not in raw run manifest; source file hashes preserved instead"]
}
File.write("#{output}/attempts.jsonl", (records + [setup]).map { |r| JSON.generate(r) + "\n" }.join)
File.write("#{output}/usage_summary.json", JSON.pretty_generate(summary))
puts JSON.generate(summary.slice("model_attempts", "setup_attempts", "new_model_calls"))
