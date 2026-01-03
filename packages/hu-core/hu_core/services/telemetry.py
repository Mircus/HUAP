"""
Telemetry utilities connecting request logging to Prometheus exporters.
"""
from __future__ import annotations

import logging
from typing import Optional

try:
    from prometheus_client import (  # type: ignore
        CollectorRegistry,
        Counter,
        Histogram,
        CONTENT_TYPE_LATEST,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when dependency missing
    CollectorRegistry = Counter = Histogram = None  # type: ignore[assignment]
    CONTENT_TYPE_LATEST = "text/plain"  # type: ignore[assignment]
    generate_latest = None  # type: ignore[assignment]
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class BaseTelemetryExporter:
    """No-op exporter used when Prometheus client is unavailable."""

    content_type = "text/plain"

    @property
    def enabled(self) -> bool:
        return False

    def record_request(
        self,
        method: str,
        path: str,
        status: int | str,
        duration_ms: float,
        pod: Optional[str],
        user: Optional[str],
    ) -> None:
        """No-op implementation."""
        return

    def export_metrics(self) -> bytes:
        """Expose a stub payload for `/metrics`."""
        return b"# telemetry_disabled 1\n"


class PrometheusTelemetryExporter(BaseTelemetryExporter):
    """Prometheus exporter that captures request counters and latency histograms."""

    content_type = CONTENT_TYPE_LATEST

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        if not PROMETHEUS_AVAILABLE:  # pragma: no cover - guarded upstream
            raise RuntimeError("prometheus_client is not installed")

        self.registry = registry or CollectorRegistry()
        self.request_counter = Counter(
            "huap_requests_total",
            "Total HUAP HTTP requests",
            ["method", "path", "status", "pod", "user"],
            registry=self.registry,
        )
        self.latency_histogram = Histogram(
            "huap_request_duration_seconds",
            "HUAP request latency in seconds",
            ["method", "path"],
            registry=self.registry,
        )

    @property
    def enabled(self) -> bool:
        return True

    def record_request(
        self,
        method: str,
        path: str,
        status: int | str,
        duration_ms: float,
        pod: Optional[str],
        user: Optional[str],
    ) -> None:
        """
        Record structured request metrics for Prometheus scrapes.
        """
        status_label = str(status)
        pod_label = pod or "unknown"
        user_label = user or "anonymous"

        self.request_counter.labels(
            method=method,
            path=path,
            status=status_label,
            pod=pod_label,
            user=user_label,
        ).inc()

        duration_seconds = max(duration_ms / 1000.0, 0.0)
        self.latency_histogram.labels(
            method=method,
            path=path,
        ).observe(duration_seconds)

    def export_metrics(self) -> bytes:
        """Expose scraped metrics in Prometheus text format."""
        if generate_latest is None:  # pragma: no cover
            return b""
        return generate_latest(self.registry)


_EXPORTER: Optional[BaseTelemetryExporter] = None


def get_telemetry_exporter() -> BaseTelemetryExporter:
    """Return the global telemetry exporter instance."""
    global _EXPORTER
    if _EXPORTER is None:
        if PROMETHEUS_AVAILABLE:
            _EXPORTER = PrometheusTelemetryExporter()
            logger.info("Telemetry exporter initialized (Prometheus)")
        else:
            logger.warning(
                "prometheus_client not installed; telemetry exporter disabled"
            )
            _EXPORTER = BaseTelemetryExporter()
    return _EXPORTER


__all__ = [
    "BaseTelemetryExporter",
    "PrometheusTelemetryExporter",
    "get_telemetry_exporter",
]
