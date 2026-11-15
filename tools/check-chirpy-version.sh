#!/usr/bin/env bash
#
# Fail if the installed Chirpy differs from .chirpy-version, the version the
# site design (_sass/_palette.scss) was last checked against.
#
# When it fails after a Chirpy release:
#   1. bundle update jekyll-theme-chirpy
#   2. bash tools/test.sh, and check the site with bundle exec jekyll s
#   3. fix _sass/_palette.scss if needed, then put the new version in
#      .chirpy-version and push

set -eu

expected="$(tr -d '[:space:]' <.chirpy-version)"
installed="$(bundle exec ruby -e 'print Gem.loaded_specs["jekyll-theme-chirpy"].version')"

if [[ $installed != "$expected" ]]; then
  msg="Chirpy $installed is installed, but the site design was checked against $expected (.chirpy-version)."
  msg+=" Update locally (bundle update jekyll-theme-chirpy), re-check the design, then bump .chirpy-version."
  if [[ -n ${GITHUB_ACTIONS:-} ]]; then
    echo "::error title=Chirpy version changed::$msg"
  else
    echo "ERROR: $msg" >&2
  fi
  exit 1
fi

echo "OK: Chirpy $installed matches .chirpy-version"
