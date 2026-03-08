# ─────────────────────────────────────────────
#  SIK Radio Configurator — production image
# ─────────────────────────────────────────────
FROM python:3.11-slim AS base

# Install OS packages needed for pyserial USB access
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libusb-1.0-0 \
       udev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── deps (cached layer) ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir \
        pyserial \
        flask \
        gunicorn

# ── application code ──────────────────────────────────────────────────────────
COPY src/           ./src/
COPY web_app.py     .
COPY templates/     ./templates/
COPY gunicorn.conf.py .

# ── runtime user (needs dialout group for serial port access) ─────────────────
# The host's dialout GID is usually 20 (macOS) or 20/dialout (Linux).
# Override at runtime with: docker run --group-add $(getent group dialout | cut -d: -f3)
RUN groupadd -g 20 dialout-app 2>/dev/null || true \
    && useradd -m -u 1001 -G dialout-app appuser

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "web_app:app"]
