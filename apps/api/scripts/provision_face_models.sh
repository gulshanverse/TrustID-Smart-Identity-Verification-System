#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="${1:-models}"
mkdir -p "$MODEL_DIR"

fetch_verified() {
  local url="$1"
  local output="$2"
  local expected="$3"
  curl --fail --location --retry 3 --connect-timeout 15 --max-time 300 "$url" -o "$output"
  local actual
  actual="$(sha256sum "$output" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "checksum mismatch for $output: expected $expected, got $actual" >&2
    rm -f "$output"
    exit 1
  fi
}

fetch_verified \
  "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" \
  "$MODEL_DIR/face_recognition_sface_2021dec.onnx" \
  "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"

fetch_verified \
  "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
  "$MODEL_DIR/face_detection_yunet_2023mar.onnx" \
  "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"

printf 'provisioned verified face models in %s\n' "$MODEL_DIR"
