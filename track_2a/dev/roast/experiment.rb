# frozen_string_literal: true
require "json"
require "fileutils"
require "digest"
require "open3"
require "timeout"
require "rbconfig"
require "securerandom"
require_relative "measurement"

module OstEval
  class Experiment
    STEPS = %w[prepare extract select predict verify grade].freeze
    attr_reader :config, :output
    def initialize
      root = File.expand_path("../../..", __dir__)
      @output = File.expand_path(ENV.fetch("ROAST_OUTPUT", "#{root}/output/roast/smoke-v2"))
      @config = { "root" => root, "output" => output, "run_id" => File.basename(output),
        "python" => ENV.fetch("ROAST_PYTHON", "python3"), "mode" => ENV.fetch("ROAST_MODE", "mock"),
        "strategy" => ENV.fetch("ROAST_STRATEGY", "full"), "input" => ENV["ROAST_INPUT"], "gold" => ENV["ROAST_GOLD"],
        "annotations" => ENV["ROAST_ANNOTATIONS"], "replay_root" => ENV["ROAST_REPLAY_ROOT"], "model" => ENV.fetch("ROAST_MODEL", "gpt-6.1-sol"), "effort" => ENV.fetch("ROAST_EFFORT", "medium"),
        "max_calls" => Integer(ENV.fetch("ROAST_MAX_CALLS", "108")), "max_retries" => Integer(ENV.fetch("ROAST_MAX_RETRIES", "0")),
        "timeout" => Float(ENV.fetch("ROAST_TIMEOUT", "120")), "time_budget" => Float(ENV.fetch("ROAST_TIME_BUDGET", "600")),
        "new_live_calls_allowed" => 0, "new_live_token_budget" => 0, "repeats" => Integer(ENV.fetch("ROAST_REPEATS", "3")),
        "test_fail_step" => ENV["ROAST_TEST_FAIL_STEP"], "test_sleep_step" => ENV["ROAST_TEST_SLEEP_STEP"],
        "test_sleep_seconds" => Float(ENV.fetch("ROAST_TEST_SLEEP_SECONDS", "2")), "test_temporary_step" => ENV["ROAST_TEST_TEMPORARY_STEP"],
        "test_crash_point" => ENV["ROAST_TEST_CRASH_POINT"],
        "test_interrupt_after" => ENV["ROAST_TEST_INTERRUPT_AFTER"] && Integer(ENV["ROAST_TEST_INTERRUPT_AFTER"]) }
      raise "only mock/replay; live requires separate approval" unless %w[mock replay].include?(config["mode"])
      raise "invalid context strategy" unless %w[full vote_pages].include?(config["strategy"])
      raise "call/retry budget exceeds policy" unless (0..108).cover?(config["max_calls"]) && (0..2).cover?(config["max_retries"])
      raise "invalid timeout/repeats" unless config["timeout"] > 0 && config["time_budget"] > 0 && (1..3).cover?(config["repeats"])
      raise "replay root + input required" if config["mode"] == "replay" && (!config["replay_root"] || !config["input"])
      FileUtils.mkdir_p(output)
      @state_path = "#{output}/stages.json"
      @state = File.exist?(@state_path) ? JSON.parse(File.read(@state_path)) : {}
      @invocation_start = Float(ENV.fetch("ROAST_INVOCATION_START", Time.now.to_f.to_s))
      config["engine_sha256"] = Digest::SHA256.hexdigest(Dir["#{root}/track_2a/src/*.py"].sort.map { |p| File.read(p) }.join)
      config["recipe_sha256"] = Digest::SHA256.hexdigest(Dir["#{__dir__}/*.{rb,py}"].sort.map { |p| File.read(p) }.join)
      atomic("#{output}/config.json", config)
    end
    def digest(path) = Digest::SHA256.file(path).hexdigest
    def atomic(path, value)
      temp = "#{path}.writing"; File.write(temp, JSON.pretty_generate(value)); File.rename(temp, path)
    end
    def event(step, status, extra = {})
      File.open("#{output}/events.jsonl", "a") { |f| f.puts(JSON.generate({ "run_id" => config["run_id"], "stage" => step, "status" => status, "utc" => Time.now.utc.iso8601 }.merge(extra))) }
    end
    def self.jsonl(path) = File.readlines(path).reject { |l| l.strip.empty? }.map { |l| JSON.parse(l) }
    def write_rows(path, rows)
      temp = "#{path}.writing"; File.write(temp, rows.map { |r| JSON.generate(r) + "\n" }.join); File.rename(temp, path)
    end
    def validate_artifacts(record)
      raise "cached artifact changed; refusing regeneration" unless record.fetch("artifacts").all? { |p, h| File.file?(p) && digest(p) == h }
    end
    def validate_sources
      prepared = @state["prepare"]
      return unless prepared && prepared["status"] == "done"
      validate_artifacts(prepared)
      path = "#{output}/source_inputs.json"
      raise "legacy cache lacks source integrity; choose fresh output" unless prepared["artifacts"].key?(path)
      sources = JSON.parse(File.read(path))
      raise "unsupported source integrity version" unless sources["version"] == 2
      sources.fetch("files").each do |p, h|
        raise "source dependency changed: #{p}; choose fresh output" unless File.file?(p) && digest(p) == h
      end
      config["source_inputs_sha256"] = digest(path)
      atomic("#{output}/config.json", config)
    end
    def fingerprint_for(step)
      previous = STEPS.take(STEPS.index(step)).to_h { |s| [s, @state[s]&.fetch("artifacts", nil)] }
      Digest::SHA256.hexdigest(JSON.generate(config.slice("engine_sha256", "recipe_sha256", "mode", "strategy", "input", "replay_root", "max_calls", "model", "effort", "source_inputs_sha256")) +
        JSON.generate(previous) + (config["input"] && File.file?(config["input"]) ? digest(config["input"]) : "fixture") +
        (step == "grade" ? digest(config["gold"] || "#{output}/evaluation/gold.jsonl") : "") +
        (step == "grade" && config["annotations"] ? digest(config["annotations"]) : ""))
    end
    def stage(step)
      raise "unknown stage" unless STEPS.include?(step)
      @current_step = step
      validate_sources
      STEPS.take(STEPS.index(step)).each do |name|
        prior = @state[name]
        raise "upstream stage incomplete: #{name}" unless prior && prior["status"] == "done"
        validate_artifacts(prior)
      end
      prior = @state[step]
      validate_artifacts(prior) if prior && prior["status"] == "done"
      fingerprint = fingerprint_for(step)
      if prior && prior["status"] == "done" && prior["fingerprint"] == fingerprint
        event(step, "cache_hit"); puts JSON.generate(stage: step, status: "cache_hit"); return
      end
      event(step, "started")
      raise "injected permanent failure" if config["test_fail_step"] == step
      raise "run time budget exhausted" if Time.now.to_f - @invocation_start > config["time_budget"]
      send(step)
      artifacts = artifact_paths(step).to_h { |p| [p, digest(p)] }
      @state[step] = { "status" => "done", "fingerprint" => fingerprint_for(step), "artifacts" => artifacts }; atomic(@state_path, @state)
      event(step, "done", "artifacts" => artifacts); puts JSON.generate(stage: step, status: "done")
    rescue StandardError => error
      event(step, "failed", "error" => error.message); raise
    end
    def artifact_paths(step)
      names = { "prepare" => %w[cases.jsonl provenance.json source_inputs.json], "extract" => %w[contexts.jsonl], "select" => %w[selected.jsonl],
                "predict" => %w[predictions.jsonl observations.jsonl case-cache-index.json budget.json], "verify" => %w[checks.jsonl], "grade" => %w[report.json] }
      paths = names.fetch(step).map { |n| "#{output}/#{n}" }
      paths += Dir["#{output}/case-cache/*.json"].sort if step == "predict"
      paths
    end
    def process(args)
      attempts = 0
      loop do
        attempts += 1; start = Process.clock_gettime(Process::CLOCK_MONOTONIC); result = nil
        event("command", "attempt_started", "attempt_id" => "#{config['run_id']}/#{@current_step || 'command'}/#{SecureRandom.uuid}/#{attempts}", "args" => args)
        remaining = config["time_budget"] - (Time.now.to_f - @invocation_start)
        raise "run time budget exhausted" unless remaining > 0
        command_timeout = [config["timeout"], remaining].min
        Open3.popen3({ "ROAST_GOLD" => nil, "API_KEY" => nil, "LLM_API_KEY" => nil, "PUBLICAI_API_KEY" => nil }, *args, pgroup: true) do |stdin, stdout, stderr, wait|
          stdin.close; reader = Thread.new { stdout.read }; err_reader = Thread.new { stderr.read }
          begin
            Timeout.timeout(command_timeout) { result = wait.value }
          rescue Timeout::Error
            Process.kill("TERM", -wait.pid) rescue nil
            begin; Timeout.timeout(1) { wait.value }; rescue Timeout::Error; Process.kill("KILL", -wait.pid) rescue nil; wait.value; end
            event("command", "timeout", "process_wall_ms" => (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000)
            raise "command timeout; usage unknown"
          end
          out = reader.value; err = err_reader.value
          File.open("#{output}/commands.log", "a") { |f| f.puts(out); f.puts(err) }
          event("command", result.success? ? "succeeded" : "failed", "exit_code" => result.exitstatus,
                "process_wall_ms" => (Process.clock_gettime(Process::CLOCK_MONOTONIC) - start) * 1000, "api_wait_ms" => nil)
          return if result.success?
          if result.exitstatus == 75 && attempts <= config["max_retries"]
            event("command", "retry", "retry" => attempts); next
          end
          raise "command exited #{result.exitstatus}: #{err.lines.last&.strip}"
        end
      end
    end
    def python(step) = process([config["python"], "#{__dir__}/worker.py", step, "--config", "#{output}/config.json"])
    def prepare
      if config["input"]
        origin = File.expand_path(config["input"])
        if config["mode"] == "replay"
          metadata = JSON.parse(File.read("#{config['replay_root']}/manifest.json"))
          expected = metadata["sample_sha256"] || metadata.dig("code_hashes", "cases.jsonl")
          raise "replay dataset hash mismatch" unless expected == digest(origin)
          dates = metadata.dig("case_counts", "date") || {}
          raise "protected final holdout; do not read cases" if dates.key?("2024-06-09") || metadata["holdout_used"] == true
        end
        rows = self.class.jsonl(origin)
        rows.each do |row|
          raise "gold fields forbidden in inference cases" unless (row.keys & %w[label entailment_label evidence expected reference_string]).empty?
          if row["booklet"]
            p = row["booklet"]["path"]; row["booklet"]["path"] = File.expand_path(p, File.dirname(origin))
          end
        end
        raise "duplicate/missing case IDs" if rows.map { |r| r["id"] }.any?(&:nil?) || rows.map { |r| r["id"] }.uniq.size != rows.size
        write_rows("#{output}/cases.jsonl", rows)
      else
        python("fixture")
      end
      raise "case budget exceeded" if config["mode"] == "mock" && self.class.jsonl("#{output}/cases.jsonl").size > config["max_calls"]
      # Inference dependency snapshots exclude evaluation gold and annotations.
      source_files = []
      source_files += Dir["#{config['root']}/track_2a/src/*.py"].sort
      source_files << File.expand_path(config["input"]) if config["input"]
      rows = self.class.jsonl("#{output}/cases.jsonl")
      rows.each { |c| source_files << c["booklet"]["path"] if c["booklet"] }
      if config["mode"] == "replay"
        source_files << "#{config['replay_root']}/manifest.json"
        %w[engine_snapshot.py predict.py source_spans.py document_selection.py selector_snapshot.py schema.json].each do |name|
          path = "#{config['replay_root']}/#{name}"; source_files << path if File.file?(path)
        end
        rows.each do |c|
          variant = c["reference"] || config["strategy"] == "full" ? "baseline" : "vote_pages"
          folder = "#{config['replay_root']}/calls/#{variant}-#{c['id']}"
          folder = "#{config['replay_root']}/calls/#{c['id']}" unless Dir.exist?(folder)
          meta = File.file?("#{folder}/success.json") ? "#{folder}/success.json" : "#{folder}/recovered_success.json"
          events = Dir["#{folder}/attempt-*-events.jsonl"].sort
          events = ["#{folder}/events.jsonl"] if events.empty?
          source_files += [meta, "#{folder}/response.json", "#{folder}/prompt.txt"] + events
        end
      end
      snapshots = source_files.uniq.sort.to_h { |p| [File.expand_path(p), digest(p)] }
      atomic("#{output}/source_inputs.json", { "version" => 2, "files" => snapshots })
      config["source_inputs_sha256"] = digest("#{output}/source_inputs.json")
      atomic("#{output}/config.json", config)
      commit, = Open3.capture2("git", "-C", config["root"], "rev-parse", "HEAD", err: File::NULL)
      diff, = Open3.capture2("git", "-C", config["root"], "diff", "--binary", "HEAD", err: File::NULL)
      files, = Open3.capture2("git", "-C", config["root"], "ls-files", "-z", "--cached", "--others", "--exclude-standard", err: File::NULL)
      tree = files.split("\0").sort.filter_map { |p| f = File.join(config["root"], p); File.file?(f) ? [p, digest(f)] : nil }.to_h
      atomic("#{output}/provenance.json", config.slice("run_id", "mode", "strategy", "model", "effort", "engine_sha256", "recipe_sha256", "max_calls", "max_retries", "timeout", "time_budget", "new_live_calls_allowed", "new_live_token_budget").merge(
        "commit" => commit.strip.empty? ? nil : commit.strip, "dirty_diff_sha256" => Digest::SHA256.hexdigest(diff),
        "worktree_content_sha256" => Digest::SHA256.hexdigest(JSON.generate(tree)), "worktree_files" => tree,
        "data_sha256" => digest("#{output}/cases.jsonl"), "split_sha256" => Digest::SHA256.hexdigest(JSON.generate({validation: %w[2020-09-27 2021-03-07 2024-03-03], final_holdout: "2024-06-09"})), "prompt_config_sha256" => Digest::SHA256.hexdigest(File.read("#{output}/config.json")), "roast_version" => "1.3.0", "ruby_version" => RUBY_VERSION,
        "gold_in_inference" => false, "final_holdout_read" => false, "validation_not_test" => true))
    end
    def extract = python("extract")
    def select = python("select")
    def predict = python("predict")
    def verify = python("verify")
    def grade
      gold_path = config["gold"] || "#{output}/evaluation/gold.jsonl"
      gold = self.class.jsonl(gold_path); preds = self.class.jsonl("#{output}/predictions.jsonl")
      tasks = %w[beginner advanced].to_h do |task|
        rows = gold.select { |r| r.fetch("task", "beginner") == task }
        [task, Metrics.classification(rows, preds).merge("ci95" => Metrics.interval(rows, preds))]
      end
      obs = self.class.jsonl("#{output}/observations.jsonl").map { |r| r.merge("usage" => Usage.read(r["usage_source"], r["raw_usage"])) }
      slices = {"claim_language" => gold.group_by { |g| g["claim_language"] || "unknown" }, "source_language" => gold.group_by { |g| g["reference_language"] || "unknown" }, "language_relation" => gold.group_by { |g| g["claim_language"] && g["reference_language"] ? (g["claim_language"] == g["reference_language"] ? "same" : "cross") : "unknown" }}.transform_values { |groups| groups.transform_values { |g| Metrics.classification(g,preds) } }
      summaries = {"local_pdf_context" => self.class.jsonl("#{output}/contexts.jsonl").map { |x| x["local_pdf_context_ms"] }, "local_selection" => self.class.jsonl("#{output}/selected.jsonl").map { |x| x["local_selection_ms"] }, "local_replay_wrapper" => obs.map { |x| x["local_replay_wall_ms"] }}.transform_values do |values|
        v = values.compact.sort
        {"count" => v.size, "unknown" => values.size-v.size, "mean_ms" => v.empty? ? nil : v.sum.fdiv(v.size), "p95_ms" => v.empty? ? nil : v[[(0.95*v.size).ceil-1,0].max]}
      end
      evidence = config["annotations"] ? Evidence.diagnostic(gold, preds, self.class.jsonl("#{output}/contexts.jsonl"), self.class.jsonl("#{output}/cases.jsonl"), self.class.jsonl(config["annotations"])) : { "verified_scope" => [], "reference_page_hit5" => nil, "reason" => "verified annotations not provided" }
      atomic("#{output}/report.json", { "run_id" => config["run_id"], "tasks" => tasks, "language_slices" => slices, "local_timing" => summaries, "api_wait_ms" => nil, "usage" => Usage.aggregate(obs),
        "attempt_observations" => obs, "replay_repeats" => config["repeats"], "independent_new_model_trials" => 0,
        "run_to_run_spread" => nil, "repeat_note" => "cached replay/deterministic mock repeats are plumbing checks, not independent inference variance",
        "official_composite_score" => nil, "official_score_unknown_reasons" => ["organizer proxy and peer normalization absent", "Apertus not assessed", "gold page coverage incomplete"],
        "gold_pages" => evidence, "new_remote_calls" => 0,
        "decision" => "plumbing only; no production promotion or live hillclimb", "data_scope" => "validation", "final_holdout_read" => false })
    end
  end
end
