#!/usr/bin/env bash

set -euo pipefail

path="$1"
mode="${2:-dev}"
a="${3:-py}"
b="${4:-sh}"

set -x

diff -r output_$a/$mode/openedx/$path output_$b/$mode/openedx/$path

