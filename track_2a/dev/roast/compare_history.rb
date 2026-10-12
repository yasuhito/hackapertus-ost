# Fixed historical paired development comparison; never runs a provider.
require_relative 'experiment'
source, imported, replay, annotation_path = ARGV
abort 'usage: compare_history.rb SOURCE IMPORTED_USAGE REPLAY_OUTPUT ANNOTATIONS' unless annotation_path
read_rows = ->(p) { OstEval::Experiment.jsonl(p) }
gold = read_rows.call("#{source}/gold.jsonl")
rows = read_rows.call("#{source}/predictions.jsonl")
usage = JSON.parse(File.read("#{imported}/usage_summary.json"))
variants = %w[baseline vote_pages].to_h do |variant|
  preds = rows.select { |r| r['variant']==variant }.map { |r| r['prediction'] }
  tasks = %w[beginner advanced].to_h do |task|
    g = gold.select { |r| r['task']==task }
    [task, OstEval::Metrics.classification(g,preds).merge('ci95'=>OstEval::Metrics.interval(g,preds))]
  end
  ev = OstEval::Evidence.diagnostic(gold,preds,read_rows.call("#{replay}/contexts.jsonl"),read_rows.call("#{replay}/cases.jsonl"),read_rows.call(annotation_path))
  [variant, {'tasks'=>tasks,'evidence'=>ev}]
end
full = usage.fetch('partitions').fetch('A_full').fetch('usage')
selected = usage.fetch('partitions').fetch('A_selected').fetch('usage')
page_full = variants['baseline']['evidence']['details'].to_h { |x| [x['id'],x['reference_page_hit5']] }
page_selected = variants['vote_pages']['evidence']['details'].to_h { |x| [x['id'],x['reference_page_hit5']] }
comparison = {'variants'=>variants, 'A_actual_usage_full'=>full, 'A_actual_usage_selected'=>selected,
  'input_reduction_percent'=>100*(1-selected.dig('input','complete_total').fdiv(full.dig('input','complete_total'))),
  'total_reduction_percent'=>100*(1-selected.dig('total','complete_total').fdiv(full.dig('total','complete_total'))),
  'B_shared_usage_counted_once'=>usage.fetch('partitions').fetch('B_shared_once'),
  'source_report_sha256'=>Digest::SHA256.file("#{source}/report.json").hexdigest,
  'reference_page_diagnostic_losses'=>page_full.keys.select { |id| page_full[id] && !page_selected[id] },
  'reference_page_diagnostic_gains'=>page_full.keys.select { |id| !page_full[id] && page_selected[id] },
  'reference_page_note'=>'Mappings cover reference-bearing pages only; losses are independent-QA flags, not proof of incorrect evidence elsewhere',
  'regressions'=>JSON.parse(File.read("#{source}/report.json"))['regressions'],
  'decision'=>'keep vote_pages as development candidate: fewer actual input tokens, no observed paired classification regressions; reference-page diagnostic has six losses/two gains requiring independent QA; production promotion waits for Apertus and independent QA',
  'estimate_separate'=>{'A_context_utf8_bytes_div4_full'=>737255,'selected'=>167033,'reduction_percent'=>77.3439},
  'api_wait_ms'=>nil,'api_wait_reason'=>'historical CLI wall time is not exact request wait',
  'official_composite_score'=>nil, 'new_model_calls'=>0, 'holdout_read'=>false,
  'limitations'=>['54 seen validation cases from two date groups; not unbiased test','cached repetitions do not estimate inference variance','GPT development eligibility unconfirmed','assistant pages are not official/human gold']}
File.write("#{imported}/comparison.json",JSON.pretty_generate(comparison))
puts JSON.generate(comparison.slice('input_reduction_percent','total_reduction_percent','new_model_calls'))
