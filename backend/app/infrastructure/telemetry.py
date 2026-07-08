"""OpenTelemetry instrumentation for the CFI platform.

Provides distributed tracing (→ Jaeger) and metrics (→ Prometheus) when
``OTEL_ENABLED=true``.  When disabled (the default), all helper functions
are safe no-ops so that CI tests and local dev runs have zero overhead.

Architecture::

    FastAPI App
      ├─ OTEL SDK (auto-instrument)
      │    ├─ Traces  ──→  Jaeger  (:4317 OTLP gRPC)  ──→  Jaeger UI (:16686)
      │    └─ Metrics ──→  /metrics endpoint
      │                         ↑
      │                  Prometheus (:9090) scrapes
      │                         ↓
      │                  Grafana (:3001) visualises
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# ── Metric Stubs ──────────────────────────────────────────────
# When OTEL is disabled these are simple no-op objects so callers
# never need to check ``if otel_enabled:`` before recording.


class _NoOpCounter:
    """Drop-in replacement that silently discards .add() calls."""

    def add(self, amount: int | float, attributes: dict | None = None) -> None:  # noqa: ARG002
        pass


class _NoOpHistogram:
    """Drop-in replacement that silently discards .record() calls."""

    def record(self, value: float, attributes: dict | None = None) -> None:  # noqa: ARG002
        pass


class _NoOpUpDownCounter:
    """Drop-in replacement that silently discards .add() calls."""

    def add(self, amount: int | float, attributes: dict | None = None) -> None:  # noqa: ARG002
        pass


# Public metric handles — always safe to use.
simulation_rounds_total: Any = _NoOpCounter()
simulation_duration_seconds: Any = _NoOpHistogram()
active_simulations: Any = _NoOpUpDownCounter()
alerts_generated_total: Any = _NoOpCounter()
http_request_duration_seconds: Any = _NoOpHistogram()


# ── Setup ─────────────────────────────────────────────────────


def setup_telemetry(app: FastAPI) -> None:
    """Initialise OpenTelemetry tracing + metrics and attach to *app*.

    This is guarded by ``settings.otel_enabled``; when ``False`` the
    function returns immediately and all metric handles remain no-ops.
    """
    from app.config import get_settings

    settings = get_settings()
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    # Import OTEL packages only when enabled to avoid ImportErrors
    # in environments that haven't installed the optional dependencies.
    try:
        import os

        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from prometheus_client import make_asgi_app as make_prometheus_app

        # Optional push metrics exporters
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            has_push_metrics = True
        except ImportError:
            has_push_metrics = False
    except ImportError as exc:
        logger.warning("OpenTelemetry packages not installed — skipping instrumentation: %s", exc)
        return

    service_name = settings.otel_service_name
    resource = Resource.create({"service.name": service_name})

    # ── Parse secure/insecure connection & headers ────────────
    endpoint = settings.otel_exporter_otlp_endpoint
    is_secure = endpoint.startswith("https://") if endpoint else False

    headers = {}
    headers_str = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    if headers_str:
        for item in headers_str.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                headers[k.strip()] = v.strip()

    # ── Tracing → Jaeger / Grafana Tempo via OTLP/gRPC ────────
    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=not is_secure,
        headers=headers,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics → Prometheus /metrics OR Grafana Cloud via OTLP ──
    metric_readers = []
    use_push_metrics = has_push_metrics and (
        is_secure or os.environ.get("OTEL_METRICS_EXPORTER") == "otlp"
    )

    if use_push_metrics:
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=endpoint,
            insecure=not is_secure,
            headers=headers,
        )
        # Export metrics every 15 seconds
        metric_readers.append(
            PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=15000)
        )
        logger.info("OpenTelemetry metrics push exporter enabled")
    else:
        metric_readers.append(PrometheusMetricReader())
        logger.info("OpenTelemetry metrics pull exporter (Prometheus scrape) enabled")

    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter("cfi.metrics", version="0.2.0")

    # Create real metric instruments and publish to module-level handles
    global simulation_rounds_total, simulation_duration_seconds  # noqa: PLW0603
    global active_simulations, alerts_generated_total, http_request_duration_seconds  # noqa: PLW0603

    simulation_rounds_total = meter.create_counter(
        name="simulation_rounds_total",
        description="Total number of FL training rounds completed",
        unit="1",
    )
    simulation_duration_seconds = meter.create_histogram(
        name="simulation_duration_seconds",
        description="Duration of each FL training round",
        unit="s",
    )
    active_simulations = meter.create_up_down_counter(
        name="active_simulations",
        description="Number of currently running simulations",
        unit="1",
    )
    alerts_generated_total = meter.create_counter(
        name="alerts_generated_total",
        description="Total number of fraud alerts generated",
        unit="1",
    )
    http_request_duration_seconds = meter.create_histogram(
        name="http_request_duration_seconds",
        description="HTTP request latency by route",
        unit="s",
    )

    # ── Auto-instrument FastAPI ────────────────────────────────
    FastAPIInstrumentor.instrument_app(app)

    # ── Mount Prometheus /metrics endpoint (only if pull reader is used) ──
    has_prometheus = any(isinstance(r, PrometheusMetricReader) for r in metric_readers)
    if has_prometheus:
        prometheus_asgi = make_prometheus_app()
        app.mount("/metrics", prometheus_asgi)
        logger.info(
            "OpenTelemetry enabled (Pull Mode) — traces → %s, metrics → /metrics",
            settings.otel_exporter_otlp_endpoint,
        )
    else:
        logger.info(
            "OpenTelemetry enabled (Push Mode) — metrics and traces pushing to OTLP endpoint: %s",
            settings.otel_exporter_otlp_endpoint,
        )
