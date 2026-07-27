#!/bin/bash
# Records a py-spy flamegraph for a pytest invocation, meant to be run inside the
# dev container (see docker/tests/compose.yml / CLAUDE.md).
#
# Usage:
#   ./docker/develop/scripts/profile-flamegraph.sh <output.svg> <pytest-args...>
#
# Example (single-shot, no pytest-benchmark repetition, one iteration/round):
#   COBBLER_PERFORMANCE_TEST_GET_AUTOINSTALL_ITERATIONS=1 \
#     ./docker/develop/scripts/profile-flamegraph.sh \
#     /code/profile-get-autoinstall-profile.svg \
#     --benchmark-only "tests/performance/get_autoinstall_test.py::test_get_autoinstall[False-profile]"
#
# py-spy is a sampling profiler: it attaches to the pytest process it spawns and
# periodically records the Python call stack, with negligible overhead on the
# profiled code. No source changes or instrumentation are required.

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <output.svg> <pytest-args...>" >&2
    exit 1
fi

OUTPUT="$1"
shift

if ! command -v py-spy >/dev/null 2>&1; then
    echo "py-spy not found, installing..."
    pip install --break-system-packages py-spy
fi

cd /code
py-spy record --rate 200 --output "$OUTPUT" -- python3 -m pytest "$@"

echo "Flamegraph written to $OUTPUT"
