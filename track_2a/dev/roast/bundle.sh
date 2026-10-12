#!/usr/bin/env bash
set -euo pipefail
recipe_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$recipe_dir/../../.." && pwd)"
export BUNDLE_GEMFILE="$recipe_dir/Gemfile"
export BUNDLE_PATH="$project_dir/vendor/roast/bundle"
export BUNDLE_USER_HOME="$project_dir/vendor/roast/user"
export BUNDLE_APP_CONFIG="$project_dir/vendor/roast/config"
export BUNDLE_FROZEN=true
ruby -e 'abort "Ruby >=3.3 and <4 required" unless Gem::Version.new(RUBY_VERSION)>=Gem::Version.new("3.3") && Gem::Version.new(RUBY_VERSION)<Gem::Version.new("4")'
exec bundle "$@"
