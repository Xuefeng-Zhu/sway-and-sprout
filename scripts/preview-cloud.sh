#!/bin/sh
# Uses Node/npm installed on this host; works from any current directory.
set -eu
cd "$(dirname "$0")/.."
npm run preview
