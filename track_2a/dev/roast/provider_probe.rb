# Pure parser/API-contract utility; no live call performed by this file.
require_relative "measurement"
module OstEval
  module ProviderProbe
    PI_FLAGS = %w[--offline --print --mode json --no-session --no-tools --no-extensions --no-mcp --no-skills --no-context-files --no-prompt-templates].freeze
    def self.pi_command(binary, model: "gpt-6.1-sol", effort: "medium")
      raise "unapproved Pi model" unless model == "gpt-6.1-sol" && effort == "medium"
      [binary, *PI_FLAGS, "--model", "openai-codex/#{model}", "--thinking", effort, "--", "Return exactly {\"label\":1,\"evidence\":[]}."]
    end
    def self.parse(events)
      usage = Usage.from_events("pi", events)
      final = events.reverse.find { |e| e['type'] == 'message_end' && e.dig('message', 'role') == 'assistant' }
      { "usage" => usage, "model" => final&.dig('message', 'model'), "provider" => final&.dig('message', 'provider'),
        "api" => final&.dig('message', 'api'), "api_wait_ms" => nil,
        "timing_note" => "CLI events alone do not expose exact HTTP request-in-flight time; report separately from subprocess wall span." }
    end
  end
end
