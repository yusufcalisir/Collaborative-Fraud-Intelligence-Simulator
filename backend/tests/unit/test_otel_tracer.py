"""Unit tests for OpenTelemetry Distributed Tracer engine, W3C headers, and Prometheus metric recorders."""

from __future__ import annotations

import pytest

from app.infrastructure.telemetry.otel_tracer import OpenTelemetryTracer, OTelSpanContext


def test_w3c_trace_context_injection_and_extraction() -> None:
    """Verifies W3C Trace Context header generation, injection, and extraction."""
    tracer = OpenTelemetryTracer(service_name="cfi-bank-client")

    # Ingest into empty header dict
    headers = tracer.inject_w3c_trace_context()
    assert "traceparent" in headers
    assert "tracestate" in headers

    traceparent = headers["traceparent"]
    assert traceparent.startswith("00-")
    parts = traceparent.split("-")
    assert len(parts) == 4
    assert len(parts[1]) == 32  # 32-hex trace ID
    assert len(parts[2]) == 16  # 16-hex span ID

    # Extract back trace_id and span_id
    extracted_trace_id, extracted_span_id = tracer.extract_w3c_trace_context(headers)
    assert extracted_trace_id == parts[1]
    assert extracted_span_id == parts[2]


def test_trace_span_lifecycle() -> None:
    """Verifies OTel trace span lifecycle, duration calculation, and status reporting."""
    tracer = OpenTelemetryTracer()

    # Successful span
    with tracer.trace_span("test_span_success", {"bank_id": "bank_a"}) as span:
        assert isinstance(span, OTelSpanContext)
        assert span.name == "test_span_success"
        assert span.attributes["bank_id"] == "bank_a"

    assert span.status == "OK"
    assert span.duration_ms >= 0.0

    # Exception span
    with (
        pytest.raises(ValueError, match="Simulated Error"),
        tracer.trace_span("test_span_failure") as err_span,
    ):
        raise ValueError("Simulated Error")

    assert err_span.status == "ERROR"
    assert err_span.attributes["error.type"] == "ValueError"


def test_6_stage_request_spans() -> None:
    """Verifies 6-stage end-to-end request pipeline trace span helpers."""
    tracer = OpenTelemetryTracer()

    s1 = tracer.ingest_transaction_span("bank_a", count=100)
    assert s1.name == "ingest_transaction"

    s2 = tracer.feature_store_span("bank_a", feature_count=7)
    assert s2.name == "feature_store_aggregation"

    s3 = tracer.local_trainer_span("bank_a", round_id=3, epochs=5)
    assert s3.name == "local_pytorch_training"

    s4 = tracer.grpc_transmit_span("bank_a", payload_size_bytes=2048)
    assert s4.name == "grpc_mtls_transmit"

    s5 = tracer.central_aggregation_span(round_id=3, client_count=4)
    assert s5.name == "central_parameter_aggregation"

    s6 = tracer.model_registry_span(version_tag="v1.2.0")
    assert s6.name == "model_registry_save"


def test_hardware_and_training_metric_recorders() -> None:
    """Verifies Prometheus hardware and training metric recorders."""
    tracer = OpenTelemetryTracer()

    hw = tracer.record_hardware_telemetry(cpu_percent=45.2, ram_mb=1024.5, gpu_memory_mb=2048.0)
    assert hw["cpu_percent"] == 45.2
    assert hw["ram_mb"] == 1024.5
    assert hw["gpu_memory_mb"] == 2048.0
    assert "timestamp" in hw

    tr = tracer.record_training_telemetry(
        round_id=5, loss=0.1234, comm_latency_ms=85.4, dp_epsilon=0.5
    )
    assert tr["round_id"] == 5
    assert tr["loss"] == 0.1234
    assert tr["comm_latency_ms"] == 85.4
    assert tr["dp_epsilon"] == 0.5
