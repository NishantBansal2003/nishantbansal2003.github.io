# frozen_string_literal: true

source "https://rubygems.org"

# Not pinned: the deploy always builds with the newest Chirpy. It fails without
# publishing if that differs from the version in .chirpy-version (the one the
# site design was checked against); see tools/check-chirpy-version.sh.
gem "jekyll-theme-chirpy", ">= 7.6.0"

gem "html-proofer", "~> 5.0", group: :test

platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

gem "wdm", "~> 0.2.0", :platforms => [:mingw, :x64_mingw, :mswin]
