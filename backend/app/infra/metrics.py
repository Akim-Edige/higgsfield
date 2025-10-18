"""Prometheus metrics."""
from prometheus_client import Counter, Gauge

# Job metrics
jobs_created_total = Counter(
    "jobs_created_total",
    "Total number of generation jobs created",
    ["tool_type", "model_key"],
)

jobs_succeeded_total = Counter(
    "jobs_succeeded_total",
    "Total number of generation jobs succeeded",
    ["tool_type", "model_key"],
)

jobs_failed_total = Counter(
    "jobs_failed_total",
    "Total number of generation jobs failed",
    ["tool_type", "model_key", "error_code"],
)

jobs_timeout_total = Counter(
    "jobs_timeout_total",
    "Total number of generation jobs that timed out",
    ["tool_type", "model_key"],
)

# Provider metrics
provider_polls_total = Counter(
    "provider_polls_total",
    "Total number of provider polls",
    ["model_key", "status"],
)

provider_errors_total = Counter(
    "provider_errors_total",
    "Total number of provider errors",
    ["error_type"],
)

# Queue metrics
queue_depth = Gauge(
    "queue_depth",
    "Current number of pending/running jobs",
)

