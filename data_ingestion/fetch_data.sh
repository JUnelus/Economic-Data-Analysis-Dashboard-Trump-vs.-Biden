#!/bin/bash

set -euo pipefail

python "$(dirname "$0")/fetch_data.py"
