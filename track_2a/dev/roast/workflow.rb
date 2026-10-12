require "rbconfig"
require "fileutils"
root = File.expand_path("../../..", __dir__)
out = File.expand_path(ENV.fetch("ROAST_OUTPUT", "#{root}/output/roast/smoke-v2"))
FileUtils.mkdir_p(out)
lock = File.open("#{out}/workflow.lock", File::RDWR | File::CREAT, 0o600)
raise "workflow already running; no duplicate execution" unless lock.flock(File::LOCK_EX | File::LOCK_NB)
at_exit { lock.close }
ENV["ROAST_INVOCATION_START"] = Time.now.to_f.to_s
stage_file = File.join(__dir__, "stage.rb")
config do
  cmd do
    fail_on_error!
    abort_on_failure!
    display!
  end
end
execute do
  cmd(:prepare) { [RbConfig.ruby, stage_file, "prepare"] }
  cmd(:extract) { [RbConfig.ruby, stage_file, "extract"] }
  cmd(:select) { [RbConfig.ruby, stage_file, "select"] }
  cmd(:predict) { [RbConfig.ruby, stage_file, "predict"] }
  cmd(:verify) { [RbConfig.ruby, stage_file, "verify"] }
  cmd(:grade) { [RbConfig.ruby, stage_file, "grade"] }
end
