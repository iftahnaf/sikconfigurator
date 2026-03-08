"""Gunicorn production configuration."""

import os
import multiprocessing

# ── binding ───────────────────────────────────────────────────────────────────
bind    = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# ── workers ───────────────────────────────────────────────────────────────────
# Serial port is a shared resource → keep workers=1 to avoid race conditions.
# If you need higher throughput on the HTTP side, use threads instead.
workers     = 1
threads     = 4
worker_class = "gthread"

# ── timeouts ──────────────────────────────────────────────────────────────────
timeout       = 120   # serial operations can be slow
graceful_timeout = 30
keepalive     = 5

# ── logging ───────────────────────────────────────────────────────────────────
accesslog   = "-"          # stdout
errorlog    = "-"          # stderr
loglevel    = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sµs'

# ── process naming ────────────────────────────────────────────────────────────
proc_name   = "sik-configurator"
