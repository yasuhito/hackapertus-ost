require_relative "experiment"
begin
  OstEval::Experiment.new.stage(ARGV.fetch(0))
rescue StandardError => error
  warn(error.message)
  exit 1
end
