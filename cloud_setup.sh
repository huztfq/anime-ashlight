#!/bin/bash
# Setup script for the Claude cloud environment that runs the daily routine (paste into the environment's
# "Setup script" box). Installs ffmpeg, the Python packages and the rounded title font.
set -e
apt-get update -qq && apt-get install -y -qq ffmpeg fonts-dejavu-core curl >/dev/null
pip install -q --break-system-packages requests pillow || pip install -q requests pillow
mkdir -p /usr/local/share/fonts
curl -fsSL -o /usr/local/share/fonts/MPLUSRounded1c-ExtraBold.ttf \
  https://github.com/google/fonts/raw/main/ofl/mplusrounded1c/MPLUSRounded1c-ExtraBold.ttf
