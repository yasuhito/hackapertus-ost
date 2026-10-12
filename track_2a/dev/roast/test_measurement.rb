require "minitest/autorun"
require "tmpdir"
require "open3"
require "json"
require_relative "measurement"
require_relative "provider_probe"

class MeasurementTest < Minitest::Test
  def test_codex_cache_reasoning_are_subsets
    u=OstEval::Usage.read('codex_cli', {'input_tokens'=>100,'output_tokens'=>20,'cached_input_tokens'=>60,'cache_write_input_tokens'=>0,'reasoning_output_tokens'=>8})
    assert_equal 120,u['total']; assert_equal 60,u['cache_read']; assert_equal 8,u['reasoning']
  end
  def test_pi_noncache_input_and_final_event_dedup
    message={'role'=>'assistant','stopReason'=>'stop','model'=>'gpt-6.1-sol','usage'=>{'input'=>40,'output'=>20,'cacheRead'=>60,'cacheWrite'=>0,'totalTokens'=>120,'reasoning'=>8}}
    u=OstEval::Usage.from_events('pi',[{'type'=>'message_start','message'=>message},{'type'=>'message_end','message'=>message},{'type'=>'agent_end','messages'=>[message]}])
    assert_equal 100,u['input']; assert_equal 120,u['total']; assert_equal 8,u['reasoning']
  end
  def test_error_default_zeros_not_measured
    e={'type'=>'message_end','message'=>{'role'=>'assistant','stopReason'=>'error','usage'=>{'input'=>0,'output'=>0,'cacheRead'=>0,'cacheWrite'=>0,'totalTokens'=>0}}}
    assert_nil OstEval::Usage.from_events('pi',[e])['total']
  end
  def test_missing_reasoning_is_unknown
    u=OstEval::Usage.read('pi',{'input'=>1,'output'=>2,'cacheRead'=>0,'cacheWrite'=>0,'totalTokens'=>3})
    assert_nil u['reasoning']; assert_equal 0,u['cache_read']
  end
  def test_aggregate_dedup_and_unknown
    a={'attempt_id'=>'a','usage'=>OstEval::Usage.read('codex_cli',{'input_tokens'=>2,'output_tokens'=>3})}
    b={'attempt_id'=>'b','usage'=>OstEval::Usage.read('codex_cli',nil)}
    x=OstEval::Usage.aggregate([a,a,b]); assert_equal 5,x['total']['known_sum'];assert_equal 1,x['total']['unknown'];assert_nil x['total']['complete_total']
  end
  def test_apertus_missing_usage_not_proxy_filled
    u=OstEval::Usage.read('apertus_chat',nil);assert_nil u['input'];assert_nil u['total']
  end
  def test_confusion_and_known_bad
    gold=3.times.map{|i|{'id'=>i.to_s,'label'=>i,'date'=>'same'}}
    preds=3.times.map{|i|{'id'=>i.to_s,'label'=>i,'label_name'=>%w[entailment neutral contradiction][i]}}
    assert_equal 1.0,OstEval::Metrics.classification(gold,preds)['macro_f1']
    preds[0]['label_name']='neutral';r=OstEval::Metrics.classification(gold,preds);assert_operator r['macro_f1'],:<,1.0;assert_equal 1,r['confusion_matrix'][0][3]
  end
  def test_duplicates_and_float_label_invalid
    gold=[{'id'=>'x','label'=>0}];pred={'id'=>'x','label'=>0,'label_name'=>'entailment'}
    assert_equal 0.0,OstEval::Metrics.classification(gold,[pred,pred])['macro_f1']
    assert_equal 0.0,OstEval::Metrics.classification(gold,[pred.merge('label'=>0.0)])['macro_f1']
  end
  def test_group_interval_reproducible
    gold=3.times.map{|i|{'id'=>i.to_s,'label'=>i,'date'=>'same'}};preds=3.times.map{|i|{'id'=>i.to_s,'label'=>i,'label_name'=>%w[entailment neutral contradiction][i]}}
    a=OstEval::Metrics.interval(gold,preds,samples:100);assert_equal a,OstEval::Metrics.interval(gold,preds,samples:100);assert_equal 1,a['groups'];assert_equal 1.0,a['low'];refute_nil a['caution']
  end

  def test_python_score_parity
    gold=3.times.map{|i|{'id'=>i.to_s,'label'=>i,'task'=>'beginner'}}
    preds=3.times.map{|i|{'id'=>i.to_s,'label'=>i,'label_name'=>%w[entailment neutral contradiction][i],'evidence'=>[],'metrics'=>{'input_tokens'=>0,'output_tokens'=>0,'inference_time_ms'=>0}}}
    script="import sys,json;sys.path.insert(0,sys.argv[1]);from score import score;d=json.load(sys.stdin);print(json.dumps(score(d['gold'],d['preds'])))"
    out,err,status=Open3.capture3(ENV.fetch('TEST_PYTHON','python3'),'-c',script,File.expand_path('../../src',__dir__),stdin_data:JSON.generate({'gold'=>gold,'preds'=>preds}))
    assert status.success?,err
    assert_in_delta JSON.parse(out).dig('macro_f1','overall','value'),OstEval::Metrics.classification(gold,preds)['macro_f1'],1e-12
  end
  def test_pi_command_isolated_and_exact
    command=OstEval::ProviderProbe.pi_command('pi');assert_includes command,'--no-tools';assert_includes command,'--no-context-files';assert_includes command,'openai-codex/gpt-6.1-sol'
    assert_raises(RuntimeError){OstEval::ProviderProbe.pi_command('pi',model:'other')}
  end
end

class WorkflowTest < Minitest::Test
  ROOT=File.expand_path('../../..',__dir__)
  def run_flow(dir,params={})
    env={'ROAST_OUTPUT'=>dir,'ROAST_PYTHON'=>ENV.fetch('TEST_PYTHON','python3')}.merge(params)
    Open3.capture3(env,'bundle','exec','roast','execute',File.join(__dir__,'workflow.rb'))
  end
  def json(path)=JSON.parse(File.read(path))
  def test_mock_resume_no_duplicate_and_unknown_real_usage
    Dir.mktmpdir do |dir|
      out,err,status=run_flow(dir);assert status.success?,out+err
      assert_equal 3,json("#{dir}/budget.json")['mock_calls']
      report=json("#{dir}/report.json");assert_nil report['usage']['total']['complete_total'];assert_nil report['official_composite_score'];assert_equal 0,report['new_remote_calls']
      out,err,status=run_flow(dir);assert status.success?,out+err;assert_equal 3,json("#{dir}/budget.json")['mock_calls'];assert_includes File.read("#{dir}/events.jsonl"),'cache_hit'
    end
  end
  def test_failure_aborts_downstream
    Dir.mktmpdir do |dir|
      out,err,status=run_flow(dir,{'ROAST_TEST_FAIL_STEP'=>'select'});refute status.success?;refute File.exist?("#{dir}/predictions.jsonl");assert_includes File.read("#{dir}/events.jsonl"),'failed'
    end
  end
  def test_budget_stops_before_prediction
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_MAX_CALLS'=>'2'});refute status.success?;refute File.exist?("#{dir}/budget.json")
    end
  end
  def test_timeout_and_retry_bound
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_TEST_SLEEP_STEP'=>'extract','ROAST_TIMEOUT'=>'0.2'});refute status.success?;assert_includes File.read("#{dir}/events.jsonl"),'timeout';refute File.exist?("#{dir}/predictions.jsonl")
    end
  end
  def test_temporary_once_retry
    Dir.mktmpdir do |dir|
      out,err,status=run_flow(dir,{'ROAST_TEST_TEMPORARY_STEP'=>'extract','ROAST_MAX_RETRIES'=>'2'});assert status.success?,out+err;assert_equal 3,json("#{dir}/budget.json")['mock_calls'];assert_includes File.read("#{dir}/events.jsonl"),'retry'
    end
  end
  def test_interrupted_prediction_resumes_cached_first_case
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_TEST_INTERRUPT_AFTER'=>'1'});refute status.success?;assert_equal 1,json("#{dir}/budget.json")['mock_calls']
      out,err,status=run_flow(dir);assert status.success?,out+err;assert_equal 3,json("#{dir}/budget.json")['mock_calls']
    end
  end
  def test_cached_artifact_tamper_fails_without_generation
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir);assert status.success?;File.write("#{dir}/predictions.jsonl",'corrupt')
      _,_,status=run_flow(dir);refute status.success?;assert_equal 3,json("#{dir}/budget.json")['mock_calls']
    end
  end
  def test_lock_prevents_duplicate_runner
    Dir.mktmpdir do |dir|
      File.open("#{dir}/workflow.lock",File::RDWR|File::CREAT,0600) do |lock|
        lock.flock(File::LOCK_EX|File::LOCK_NB);_,_,status=run_flow(dir);refute status.success?;refute File.exist?("#{dir}/budget.json")
      end
    end
  end

  def test_gold_change_does_not_recompute_inference
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir);assert status.success?
      before=File.read("#{dir}/predictions.jsonl")
      gold=File.readlines("#{dir}/evaluation/gold.jsonl").map{|l|JSON.parse(l)}
      gold.each{|r|r['label']=2};File.write("#{dir}/changed-gold.jsonl",gold.map{|r|JSON.generate(r)+"\n"}.join)
      out,err,status=run_flow(dir,{'ROAST_GOLD'=>"#{dir}/changed-gold.jsonl"});assert status.success?,out+err
      assert_equal before,File.read("#{dir}/predictions.jsonl");assert_equal 3,json("#{dir}/budget.json")['mock_calls']
      assert_equal 0.0,json("#{dir}/report.json").dig('tasks','advanced','macro_f1')
    end
  end
  def test_gold_fields_rejected_from_input
    Dir.mktmpdir do |dir|
      File.write("#{dir}/bad-cases.jsonl",JSON.generate({'id'=>'bad','label'=>0})+"\n")
      _,_,status=run_flow("#{dir}/run",{'ROAST_INPUT'=>"#{dir}/bad-cases.jsonl"});refute status.success?;refute File.exist?("#{dir}/run/budget.json")
    end
  end
  def test_limits_and_live_mode_rejected
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_MODE'=>'live'});refute status.success?
      _,_,status=run_flow(dir,{'ROAST_MAX_RETRIES'=>'3'});refute status.success?
    end
  end
end

class EvidenceTest < Minitest::Test
  def evidence_fixture
    Dir.mktmpdir do |dir|
      path="#{dir}/fixture.pdf";File.write(path,'local-fake-pdf-hash-only')
      a={'id'=>'A','review_kind'=>'assistant_direct_source_review','approved_pages'=>[2],'pdf_sha256'=>Digest::SHA256.file(path).hexdigest,'page_text_sha256'=>{'2'=>Digest::SHA256.hexdigest('quote')}}
      yield [{'id'=>'A','label'=>0,'task'=>'advanced'},{'id'=>'U','label'=>2,'task'=>'advanced'}], [{'id'=>'A','evidence'=>[{'page'=>2,'text'=>'quote'}]}], [{'id'=>'A','pages'=>['other','quote']}], [{'id'=>'A','booklet'=>{'path'=>path}}], [a]
    end
  end
  def test_partial_verified_coverage_and_hit5
    evidence_fixture do |*args|
      r=OstEval::Evidence.diagnostic(*args);assert_equal 1,r['verified_count'];assert_equal 1,r['excluded_unverified'];assert_equal 1.0,r['reference_page_hit5'];assert_equal 0,r['human_verified_count'];assert_nil r['official_evidence_score']
      args[1][0]['evidence']=[{'page'=>1,'text'=>'other'}]*5+[{'page'=>2,'text'=>'quote'}]
      assert_equal 0.0,OstEval::Evidence.diagnostic(*args)['reference_page_hit5']
    end
  end
  def test_fuzzy_annotation_excluded
    evidence_fixture do |*args|
      args[4][0]['review_kind']='fuzzy_pending_human_review'
      assert_nil OstEval::Evidence.diagnostic(*args)['reference_page_hit5']
    end
  end
  def test_hash_mismatch_and_duplicate_refused
    evidence_fixture do |*args|
      args[4] << args[4][0].dup;assert_raises(RuntimeError){OstEval::Evidence.diagnostic(*args)}
      args[4].pop;args[4][0]['pdf_sha256']='wrong';assert_raises(RuntimeError){OstEval::Evidence.diagnostic(*args)}
    end
  end
end

class BudgetClockTest < Minitest::Test
  def test_process_stops_at_remaining_run_budget
    require_relative 'experiment'
    Dir.mktmpdir do |dir|
      env={'ROAST_OUTPUT'=>dir,'ROAST_TIME_BUDGET'=>'0.2','ROAST_TIMEOUT'=>'5','ROAST_INVOCATION_START'=>Time.now.to_f.to_s}
      old=env.to_h { |k,v| [k,ENV[k]] };env.each { |k,v| ENV[k]=v }
      begin
        e=OstEval::Experiment.new
        start=Process.clock_gettime(Process::CLOCK_MONOTONIC)
        assert_raises(RuntimeError) { e.process([RbConfig.ruby,'-e','sleep 2']) }
        assert_operator Process.clock_gettime(Process::CLOCK_MONOTONIC)-start,:<,1.5
        events=File.readlines("#{dir}/events.jsonl").map { |l| JSON.parse(l) }
        assert events.any? { |r| r['status']=='timeout' }
      ensure
        old.each { |k,v| ENV[k]=v }
      end
    end
  end
end

class CacheIntegrityRegressionTest < WorkflowTest
  # Reuse workflow helper without inheriting/rerunning all base tests.
  WorkflowTest.public_instance_methods(false).each { |name| undef_method(name) if name.to_s.start_with?('test_') }
  def tamper_case(dir,rehash: false)
    cache=Dir["#{dir}/case-cache/*.json"].first
    item=json(cache);item['prediction'].merge!('label'=>1,'label_name'=>'neutral','evidence'=>[])
    item['observation'].merge!('usage_source'=>'codex_cli','raw_usage'=>{'input_tokens'=>100,'output_tokens'=>20})
    File.write(cache,JSON.generate(item))
    if rehash
      index=json("#{dir}/case-cache-index.json");index['entries'][File.basename(cache,'.json')]['sha256']=Digest::SHA256.file(cache).hexdigest
      File.write("#{dir}/case-cache-index.json",JSON.generate(index))
    end
  end
  def test_interrupted_cache_tamper_rejected_before_more_calls
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_TEST_INTERRUPT_AFTER'=>'1'});refute status.success?
      tamper_case(dir);_,_,status=run_flow(dir);refute status.success?
      assert_equal 1,json("#{dir}/budget.json")['mock_calls'];refute File.exist?("#{dir}/report.json")
      assert_includes File.read("#{dir}/commands.log"),'case cache integrity mismatch'
    end
  end
  def test_rehashed_cache_still_checked_against_raw_source
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_TEST_INTERRUPT_AFTER'=>'1'});refute status.success?
      tamper_case(dir,rehash:true);_,_,status=run_flow(dir);refute status.success?
      assert_equal 1,json("#{dir}/budget.json")['mock_calls'];assert_includes File.read("#{dir}/commands.log"),'case cache raw response/usage/source mismatch'
    end
  end
  def test_source_pdf_change_rejected_without_resetting_fixture
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir);assert status.success?
      before=File.read("#{dir}/report.json");pdf="#{dir}/fixture.pdf"
      File.binwrite(pdf,File.binread(pdf).gsub('ZWEITE','ANDERS'));changed=Digest::SHA256.file(pdf).hexdigest
      out,err,status=run_flow(dir);refute status.success?;assert_includes out+err,'source dependency changed'
      assert_equal changed,Digest::SHA256.file(pdf).hexdigest;assert_equal before,File.read("#{dir}/report.json")
      assert_equal 3,json("#{dir}/budget.json")['mock_calls']
    end
  end
  def test_upstream_context_tamper_after_interruption_rejected
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_TEST_INTERRUPT_AFTER'=>'1'});refute status.success?
      File.write("#{dir}/contexts.jsonl",'changed')
      _,_,status=run_flow(dir);refute status.success?;assert_equal 1,json("#{dir}/budget.json")['mock_calls']
    end
  end
  def test_unknown_reserved_attempts_do_not_repeat
    %w[after_reserve after_cache_write].each do |point|
      Dir.mktmpdir do |dir|
        _,_,status=run_flow(dir,{'ROAST_TEST_CRASH_POINT'=>point});refute status.success?
        assert_equal 1,json("#{dir}/budget.json")['mock_calls']
        _,_,status=run_flow(dir);refute status.success?;assert_equal 1,json("#{dir}/budget.json")['mock_calls'];refute File.exist?("#{dir}/report.json")
      end
    end
  end
  def test_durable_cache_with_reserved_ledger_recovers_without_duplicate
    Dir.mktmpdir do |dir|
      _,_,status=run_flow(dir,{'ROAST_TEST_CRASH_POINT'=>'after_index_write'});refute status.success?
      assert_equal 1,json("#{dir}/budget.json")['mock_calls']
      out,err,status=run_flow(dir);assert status.success?,out+err
      assert_equal 3,json("#{dir}/budget.json")['mock_calls'];assert_equal 3,json("#{dir}/case-cache-index.json")['entries'].size
    end
  end
end

class ExternalInputIntegrityTest < WorkflowTest
  WorkflowTest.public_instance_methods(false).each { |name| undef_method(name) if name.to_s.start_with?('test_') }
  def test_external_reference_content_change_stops_before_cached_inference
    Dir.mktmpdir do |dir|
      cases="#{dir}/input.jsonl";gold="#{dir}/gold.jsonl";target="#{dir}/run"
      File.write(cases,JSON.generate({'id'=>'B','reference'=>{'text'=>'Ja'},'claim'=>{'text'=>'Ja'}})+"\n")
      File.write(gold,JSON.generate({'id'=>'B','label'=>0,'task'=>'beginner','date'=>'fixture'})+"\n")
      params={'ROAST_INPUT'=>cases,'ROAST_GOLD'=>gold}
      out,err,status=run_flow(target,params);assert status.success?,out+err
      before=File.read("#{target}/predictions.jsonl");File.write(cases,File.read(cases).sub('Ja','Nein'))
      out,err,status=run_flow(target,params);refute status.success?;assert_includes out+err,'source dependency changed'
      assert_equal before,File.read("#{target}/predictions.jsonl");assert_equal 1,json("#{target}/budget.json")['mock_calls']
    end
  end
end
