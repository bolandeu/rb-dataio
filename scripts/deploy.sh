#!/bin/sh
# deploy_command of Antagor (`antagor publish`): push main with tags, install the tag on this Mac,
# and tell the tools root agent about the release.
# Antagor runs commands without a shell, so && and stdin live here. ANTAGOR_VERSION is the new tag.
set -e
git push origin main --follow-tags
uv tool install --force --quiet "rb-dataio @ git+$(git remote get-url origin)@$ANTAGOR_VERSION" && dataio --version || echo "warning: local install of $ANTAGOR_VERSION failed" >&2
n="$(git rev-parse --show-toplevel)/../scripts/notify_release.sh"
[ -x "$n" ] || n="$HOME/Work/tools/scripts/notify_release.sh"
sha="$(git rev-parse HEAD)"
[ -x "$n" ] && echo "refs/tags/$ANTAGOR_VERSION $sha refs/tags/$ANTAGOR_VERSION 0000000000000000000000000000000000000000" | "$n" dataio
exit 0
