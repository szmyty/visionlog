from dataclasses import dataclass, field
from typing import List, Optional

from visionlog.visionlog import Enricher, Processor


@dataclass
class LoggerConfig:
    """Structured configuration object for :func:`~visionlog.get_logger`.

    Group all logger-creation options into a single, reusable configuration
    object.  Pass an instance to :func:`~visionlog.get_logger` instead of
    (or in addition to) individual keyword arguments.

    Attributes:
        service_name: Identifies the service or application emitting logs.
        user_id: Optional user identity to bind to every log record.
        session_id: Optional session identifier to bind to every log record.
        privacy_mode: When ``True`` (default), disables all PII enrichment
            (IP lookup, geo-location, device detection).
        disable_network: When ``True``, skips all outbound HTTP calls used
            for IP/geo enrichment.  Useful in CI or air-gapped environments.
        enrichers: Optional list of :class:`~visionlog.Enricher` instances
            applied after built-in enrichment.
        environment: Optional deployment environment label (e.g.
            ``"production"``, ``"staging"``).
        renderer_name: Name of the built-in renderer to use.  Supported
            values are ``"json"`` (default), ``"console"``, and ``"logfmt"``.
            Ignored when ``renderer`` is also provided.
        renderer: Optional structlog processor used as the final renderer.
            When provided, takes precedence over ``renderer_name``.
            When ``None`` the renderer selected by ``renderer_name`` is used.
        extra_processors: Optional list of additional structlog processors
            injected into the pipeline after the core processors and before
            the renderer.  Use this to extend the processor pipeline with
            custom logic without replacing the built-in defaults.
    """

    service_name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    privacy_mode: bool = True
    disable_network: bool = False
    enrichers: List[Enricher] = field(default_factory=list)
    environment: Optional[str] = None
    renderer_name: str = "json"
    renderer: Optional[object] = None
    extra_processors: Optional[List[Processor]] = None
