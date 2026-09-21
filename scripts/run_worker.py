#!/usr/bin/env python3
"""
Blood Hub Authoritative Background Worker
Polls and processes wave timeouts, request expirations, and stale assignment reconciliation.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bloodhub.worker.scheduler import run_worker_daemon

if __name__ == "__main__":
    interval = int(os.getenv("WORKER_POLL_INTERVAL", "5"))
    run_worker_daemon(poll_interval_seconds=interval)
