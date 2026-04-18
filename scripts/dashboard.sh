#!/usr/bin/env bash
# 主力資金類股輪動 Streamlit 儀表板 — 一鍵啟動/關閉
# 用法：./scripts/dashboard.sh [start|stop|restart|status]（無參數 = start）

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP="$ROOT_DIR/scripts/sector_flow_dashboard.py"
PID_FILE="/tmp/taiwan_dashboard.pid"
LOG_FILE="/tmp/taiwan_dashboard.log"
PORT=8501
URL="http://localhost:${PORT}"

c_g=$'\033[32m'; c_r=$'\033[31m'; c_y=$'\033[33m'; c_b=$'\033[36m'; c_0=$'\033[0m'
PYTHON_DESC=""
PYTHON_CMD=()

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid; pid=$(cat "$PID_FILE" 2>/dev/null || true)
  [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null
}

probe_python() {
  local label="$1"
  shift

  {
    echo "=== python candidate: $label ==="
    "$@" - <<'PY'
import importlib.util
import os
import platform
import sys

print(f"python={sys.executable}")
print(f"cwd={os.getcwd()}")
print(f"platform_machine={platform.machine()}")
for name in ("numpy", "pandas", "streamlit"):
    spec = importlib.util.find_spec(name)
    origin = getattr(spec, "origin", None) if spec else None
    print(f"{name}_spec={origin}")

import numpy as np
import pandas as pd
import streamlit

print(f"numpy={np.__file__}")
print(f"pandas={pd.__file__}")
print(f"streamlit={streamlit.__file__}")
PY
  } >>"$LOG_FILE" 2>&1
  local status=$?
  echo "preflight_exit=$status" >>"$LOG_FILE"
  echo >>"$LOG_FILE"

  if [[ $status -eq 0 ]]; then
    PYTHON_DESC="$label"
    PYTHON_CMD=("$@")
    return 0
  fi

  return 1
}

select_python() {
  local candidate
  : >"$LOG_FILE"

  if [[ "$(uname -s)" == "Darwin" ]] && command -v arch >/dev/null 2>&1 && [[ -x /usr/bin/python3 ]]; then
    if probe_python "arch -arm64 /usr/bin/python3" arch -arm64 /usr/bin/python3; then
      return 0
    fi
  fi

  for candidate in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
    else
      candidate="$(command -v "$candidate" 2>/dev/null || true)"
      [[ -n "$candidate" ]] || continue
    fi

    if probe_python "$candidate" "$candidate"; then
      return 0
    fi
  done

  return 1
}

start() {
  if is_running; then
    echo "${c_y}⚠ 已在運行${c_0} (PID $(cat "$PID_FILE"))，URL: ${URL}"
    open "$URL" 2>/dev/null || true
    return 0
  fi
  [[ -f "$APP" ]] || { echo "${c_r}✗ 找不到 $APP${c_0}"; exit 1; }

  echo "${c_b}▶ 啟動儀表板…${c_0}"
  cd "$ROOT_DIR"

  # Preflight candidate Python interpreters and pick the first one that can
  # import the packages Streamlit needs in the current architecture.
  select_python || {
    echo "${c_r}✗ Python 環境預檢失敗，檢查 $LOG_FILE${c_0}"
    tail -80 "$LOG_FILE"
    exit 1
  }
  echo "${c_b}• 使用 Python: ${PYTHON_DESC}${c_0}"

  nohup "${PYTHON_CMD[@]}" -m streamlit run "$APP" \
      --server.headless=true \
      --server.port="$PORT" \
      --browser.gatherUsageStats=false \
      >>"$LOG_FILE" 2>&1 &
  local pid=$!
  echo "$pid" >"$PID_FILE"

  # 等待 port 起來（最多 15 秒）
  for i in {1..30}; do
    if curl -sf "$URL" >/dev/null 2>&1; then
      echo "${c_g}✓ 已啟動${c_0} PID=$pid | URL=${URL} | Log=${LOG_FILE}"
      open "$URL" 2>/dev/null || true
      return 0
    fi
    kill -0 "$pid" 2>/dev/null || { echo "${c_r}✗ 啟動失敗，檢查 $LOG_FILE${c_0}"; rm -f "$PID_FILE"; tail -20 "$LOG_FILE"; exit 1; }
    sleep 0.5
  done
  echo "${c_y}⚠ 啟動逾時，但 process 仍在（PID=${pid}）。手動檢查 ${URL}${c_0}"
}

stop() {
  if ! is_running; then
    echo "${c_y}⚠ 未運行${c_0}"
    rm -f "$PID_FILE"
    # 保險：清掉同 port 上的 streamlit 殘留
    pkill -f "streamlit run .*sector_flow_dashboard.py" 2>/dev/null || true
    return 0
  fi
  local pid; pid=$(cat "$PID_FILE")
  echo "${c_b}■ 停止 PID=${pid}…${c_0}"
  kill "$pid" 2>/dev/null || true
  for i in {1..20}; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  pkill -f "streamlit run .*sector_flow_dashboard.py" 2>/dev/null || true
  echo "${c_g}✓ 已停止${c_0}"
}

status() {
  if is_running; then
    echo "${c_g}● 運行中${c_0} PID=$(cat "$PID_FILE") | URL=${URL}"
  else
    echo "${c_r}○ 未運行${c_0}"
  fi
}

case "${1:-start}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  *) echo "用法：$0 [start|stop|restart|status]"; exit 2 ;;
esac
