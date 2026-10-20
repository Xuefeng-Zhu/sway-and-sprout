#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p test-results
npm run test:e2e > test-results/browser-tests.log 2>&1
