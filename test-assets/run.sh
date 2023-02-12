#!/usr/bin/env bash

set -eou pipefail
set -x

output_id="$1"
output="test-assets/output_$output_id"
rm -rf "$output"
mkdir "$output"

test_paths=(
	"/openedx/staticfiles"
	"/openedx/themes"
)

# Most thorough check. Will do for final test:
#test_paths+=("/openedx/edx-platform")

# Less-thorough check. Better for debugging:
test_paths+=(
	"/openedx/edx-platform/common/static/bundles"
	"/openedx/edx-platform/common/static/common/css"
	"/openedx/edx-platform/common/static/js/vendor"
	"/openedx/edx-platform/common/static/xmodule"
	"/openedx/edx-platform/lms/static/certificates/css"
	"/openedx/edx-platform/lms/static/css"
	"/openedx/edx-platform/cms/static/css"
)

test_mode ( ) {
	mode="$1"
	mkdir "$output/$mode"
	tutor "$mode" start -d lms
	for path in "${test_paths[@]}" ; do 
		outpath="$output/${mode}${path}"
		mkdir -p "$(dirname "$outpath")"
		#tutor "$mode" copyfrom lms "$path" "$outpath"
		docker cp "tutor_nightly_${mode}-lms-1:$path" "$outpath"
	done
	tutor "$mode" stop
}


tutor config save \
	--set EDX_PLATFORM_REPOSITORY=https://github.com/kdmccormick/edx-platform \
	--set EDX_PLATFORM_VERSION=kdmccormick/assets-sh
tutor images build openedx
tutor dev dc build lms
test_mode local
test_mode dev
#test_mode k8s # TODO

