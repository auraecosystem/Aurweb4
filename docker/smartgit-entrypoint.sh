#!/bin/bash
set -eou pipefail

git config --global --add safe.directory /aurweb/aur.git
aurweb-config set serve repo-path '/aurweb/aur.git/'

exec "$@"
