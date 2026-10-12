# frozen_string_literal: true
require "json"
require "digest"
require "time"

module OstEval
  module Usage
    FIELDS = %w[input output cache_read cache_write reasoning total].freeze
    def self.number(value)
      value.is_a?(Numeric) && value.finite? && value >= 0 ? value : nil
    end
    def self.read(source, raw, successful: true)
      values = FIELDS.to_h { |key| [key, nil] }
      return values.merge("source" => source, "raw" => raw) unless raw.is_a?(Hash) && successful
      case source
      when "codex_cli"
        %w[input output].each { |k| values[k] = number(raw["#{k}_tokens"]) }
        values["cache_read"] = number(raw["cached_input_tokens"])
        values["cache_write"] = number(raw["cache_write_input_tokens"])
        values["reasoning"] = number(raw["reasoning_output_tokens"])
      when "pi"
        values["cache_read"] = number(raw["cacheRead"])
        values["cache_write"] = number(raw["cacheWrite"])
        fresh = number(raw["input"])
        if [fresh, values["cache_read"], values["cache_write"]].all?
          values["input"] = fresh + values["cache_read"] + values["cache_write"]
        end
        values["output"] = number(raw["output"])
        values["reasoning"] = number(raw["reasoning"])
        values["total"] = number(raw["totalTokens"])
      when "apertus_chat"
        values["input"] = number(raw["prompt_tokens"])
        values["output"] = number(raw["completion_tokens"])
        values["cache_read"] = number(raw.dig("prompt_tokens_details", "cached_tokens"))
        values["reasoning"] = number(raw.dig("completion_tokens_details", "reasoning_tokens"))
        values["total"] = number(raw["total_tokens"])
      end
      if values["total"].nil? && values["input"] && values["output"]
        values["total"] = values["input"] + values["output"]
      end
      values.merge("source" => source, "raw" => raw, "semantics" => "input includes cache; output includes reasoning; do not add subsets to total")
    end
    def self.aggregate(attempts)
      unique = attempts.uniq { |r| r.fetch("attempt_id") }
      FIELDS.to_h do |key|
        known = unique.filter_map { |r| number(r.dig("usage", key)) }
        [key, { "known_sum" => known.sum, "known" => known.size, "unknown" => unique.size - known.size,
                "complete_total" => known.size == unique.size ? known.sum : nil }]
      end
    end
    def self.from_events(source, events)
      if source == "codex_cli"
        terminal = events.reverse.find { |e| e["type"] == "turn.completed" }
        return read(source, terminal && terminal["usage"])
      end
      if source == "pi"
        endings = events.select { |e| e["type"] == "message_end" && e.dig("message", "role") == "assistant" }
        return read(source, nil) if endings.empty?
        normalized = endings.map do |event|
          message = event.fetch("message")
          read(source, message["usage"], successful: %w[stop length].include?(message["stopReason"]))
        end
        values = FIELDS.to_h do |key|
          nums = normalized.map { |r| r[key] }
          [key, nums.all? ? nums.sum : nil]
        end
        return values.merge("source" => source, "raw" => endings, "semantics" => "only final assistant message_end counted; agent_end duplicates ignored")
      end
      read(source, nil)
    end
  end

  module Metrics
    def self.classification(gold, predictions)
      raise "duplicate gold IDs" unless gold.map { |r| r.fetch("id") }.uniq.size == gold.size
      grouped = predictions.group_by { |r| r["id"] }
      matrix = Array.new(3) { Array.new(4, 0) }
      gold.each do |g|
        rows = grouped[g.fetch("id")]
        p = rows && rows.size == 1 ? rows.first : nil
        valid = p && !p.key?("error") && p["label"].is_a?(Integer) && [0, 1, 2].include?(p["label"]) &&
                p["label_name"] == %w[entailment neutral contradiction][p["label"]]
        y = valid ? p["label"] : 3
        matrix[g.fetch("label")][y] += 1
      end
      classes = 3.times.map do |label|
        tp = matrix[label][label]
        fp = 3.times.sum { |i| i == label ? 0 : matrix[i][label] }
        fn = matrix[label].sum - tp
        precision = tp + fp > 0 ? tp.to_f / (tp + fp) : 0.0
        recall = tp + fn > 0 ? tp.to_f / (tp + fn) : 0.0
        f1 = 2 * tp + fp + fn > 0 ? 2.0 * tp / (2 * tp + fp + fn) : 0.0
        { "label" => label, "precision" => precision, "recall" => recall, "f1" => f1 }
      end
      { "n" => gold.size, "macro_f1" => classes.sum { |r| r["f1"] } / 3, "classes" => classes,
        "confusion_matrix" => matrix, "matrix_columns" => %w[entailment neutral contradiction invalid_or_missing] }
    end
    def self.interval(gold, predictions, samples: 1000, seed: 1729)
      groups = gold.group_by { |r| r["date"] || r["source_row"] || r["id"] }
      keys = groups.keys
      return { "low" => nil, "high" => nil, "groups" => 0 } if keys.empty?
      by_id = predictions.group_by { |r| r["id"] }
      rng = Random.new(seed)
      scores = samples.times.map do
        gs = []; ps = []
        keys.size.times do |draw|
          groups.fetch(keys[rng.rand(keys.size)]).each do |g|
            id = "#{draw}:#{g['id']}"
            gs << g.merge("id" => id)
            Array(by_id[g['id']]).each { |p| ps << p.merge("id" => id) }
          end
        end
        classification(gs, ps)["macro_f1"]
      end.sort
      { "low" => scores[(0.025 * (scores.size - 1)).floor], "high" => scores[(0.975 * (scores.size - 1)).ceil],
        "groups" => keys.size, "samples" => samples, "seed" => seed, "method" => "date-group bootstrap; translations/paired A-B stay grouped",
        "caution" => keys.size < 10 ? "few independent date groups; not inference-variance or generalization proof" : nil }
    end
  end
end

module OstEval
  module Evidence
    def self.diagnostic(gold, predictions, contexts, cases, annotations)
      rows = gold.select { |g| g.fetch("task", "beginner") == "advanced" && [0, 2].include?(g["label"]) }
      raise "duplicate annotations" unless annotations.map { |a| a['id'] }.uniq.size == annotations.size
      approved = annotations.select { |a| a['review_kind'] == 'assistant_direct_source_review' || a['review_kind'] == 'human_direct_source_review' }.to_h { |a| [a['id'], a] }
      bypred = predictions.to_h { |r| [r['id'], r] }; bycontext = contexts.to_h { |r| [r['id'], r] }; bycase = cases.to_h { |r| [r['id'], r] }
      results = rows.filter_map do |g|
        a = approved[g['id']]; next unless a
        c = bycase.fetch(g['id']); pages = bycontext.fetch(g['id'])['pages']
        raise "annotation PDF hash mismatch" unless Digest::SHA256.file(c.fetch('booklet').fetch('path')).hexdigest == a['pdf_sha256']
        a.fetch('approved_pages').each do |n|
          raise "annotation page hash mismatch" unless n.is_a?(Integer) && n > 0 && n <= pages.size && Digest::SHA256.hexdigest(pages[n-1]) == a.fetch('page_text_sha256').fetch(n.to_s)
        end
        pred = bypred[g['id']]
        hit = pred && !pred.key?('error') && pred.fetch('evidence', []).first(5).any? do |e|
          n = e['page']; text = e['text']; n.is_a?(Integer) && a['approved_pages'].include?(n) && text.is_a?(String) && !text.strip.empty? && text.length <= 5000 && pages[n-1].include?(text)
        end
        {'id'=>g['id'], 'reference_page_hit5'=>!!hit, 'approved_pages'=>a['approved_pages'], 'review_kind'=>a['review_kind']}
      end
      {'verified_scope'=>results.map { |r| r['id'] }, 'eligible_nonneutral'=>rows.size, 'verified_count'=>results.size,
       'excluded_unverified'=>rows.size-results.size, 'reference_page_hit5'=>results.empty? ? nil : results.count { |r| r['reference_page_hit5'] }.fdiv(results.size),
       'human_verified_count'=>results.count { |r| r['review_kind']=='human_direct_source_review' }, 'details'=>results,
       'official_evidence_score'=>nil, 'scope_note'=>'Reference-bearing page and exact quote diagnostic; equivalent evidence elsewhere may be valid. This does not grade semantic sufficiency or establish official/human gold.'}
    end
  end
end
