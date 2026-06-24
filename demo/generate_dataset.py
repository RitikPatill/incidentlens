"""Generate 500 synthetic incident tickets across 8 hidden risk themes."""
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

random.seed(42)

THEMES = [
    {
        "name": "auth_failures",
        "titles": [
            "SSO login failure for user",
            "MFA token rejected",
            "OAuth callback error",
            "LDAP bind failure",
            "Session token expired unexpectedly",
        ],
        "descriptions": [
            "Multiple users unable to authenticate via SSO provider; error code 401 returned.",
            "MFA push notification not delivered; users locked out after retry limit.",
            "OAuth redirect callback returning invalid_grant; affects new sign-ups.",
            "LDAP service unreachable; corporate directory authentication failing.",
            "Session tokens expiring prematurely causing repeated logouts.",
        ],
        "severities": ["medium", "medium", "high", "high", "critical"],
        "sources": ["security", "support", "monitoring"],
    },
    {
        "name": "payment_errors",
        "titles": [
            "Checkout payment declined",
            "Billing service timeout",
            "Stripe webhook delivery failure",
            "Invoice generation error",
            "Duplicate charge detected",
        ],
        "descriptions": [
            "Payment processor returning decline codes for valid cards; revenue impact.",
            "Billing microservice not responding within SLA; checkout blocked.",
            "Stripe webhook events not processed; subscription states out of sync.",
            "PDF invoice generation fails for enterprise accounts with custom templates.",
            "Idempotency key collision causing duplicate charges for some customers.",
        ],
        "severities": ["high", "high", "medium", "low", "critical"],
        "sources": ["monitoring", "support", "on-call"],
    },
    {
        "name": "latency_spikes",
        "titles": [
            "API p99 latency exceeds SLA",
            "Database query timeout",
            "CDN cache miss rate elevated",
            "Slow search response times",
            "GraphQL resolver bottleneck",
        ],
        "descriptions": [
            "REST API p99 latency above 2 s threshold; downstream services timing out.",
            "Postgres query plan regression after statistics update; slow full-table scans.",
            "CDN cache miss rate jumped to 80%; origin servers under elevated load.",
            "Elasticsearch query latency degraded; full-text search taking >5 s.",
            "N+1 query pattern in GraphQL resolvers causing cascading DB load.",
        ],
        "severities": ["medium", "high", "medium", "medium", "high"],
        "sources": ["monitoring", "on-call"],
    },
    {
        "name": "data_pipeline",
        "titles": [
            "ETL job failed to complete",
            "Stale data in analytics dashboard",
            "Kafka consumer lag growing",
            "Data warehouse sync error",
            "Schema migration blocked",
        ],
        "descriptions": [
            "Nightly ETL pipeline exited with code 1; downstream reports show yesterday's data.",
            "Analytics dashboard serving 6-hour-old data; pipeline stuck on transform step.",
            "Kafka consumer group lagging by 500k messages; real-time features degraded.",
            "Snowflake sync job failed due to malformed JSON in source records.",
            "Alembic migration blocked by long-running transaction; deployment paused.",
        ],
        "severities": ["medium", "low", "high", "medium", "high"],
        "sources": ["monitoring", "on-call", "support"],
    },
    {
        "name": "disk_pressure",
        "titles": [
            "Disk usage exceeds 90%",
            "Log volume quota reached",
            "Object storage bucket near limit",
            "Database WAL size growing",
            "Container ephemeral storage full",
        ],
        "descriptions": [
            "Production DB server disk at 92%; write operations at risk of failure.",
            "Log aggregation bucket exceeded allocated quota; logs being dropped.",
            "S3 bucket approaching account-level storage limit; uploads may fail.",
            "Postgres WAL files accumulating faster than archiving; replication at risk.",
            "Kubernetes pod ephemeral storage limit reached; pod eviction imminent.",
        ],
        "severities": ["high", "medium", "medium", "high", "critical"],
        "sources": ["monitoring", "on-call"],
    },
    {
        "name": "deployment_issues",
        "titles": [
            "CrashLoopBackOff on new deployment",
            "Rollback triggered after failed canary",
            "Image pull error in production",
            "Config map mismatch post-deploy",
            "Health check failing on new pods",
        ],
        "descriptions": [
            "New service version entering CrashLoopBackOff; previous version rolled back.",
            "Canary deployment showing elevated error rate; automated rollback initiated.",
            "Container registry returning 403; pods unable to pull updated image.",
            "Environment variable missing from ConfigMap after deployment; app misconfigured.",
            "Liveness probe endpoint returning 500 on new pods; traffic not shifting.",
        ],
        "severities": ["critical", "high", "high", "medium", "medium"],
        "sources": ["on-call", "monitoring"],
    },
    {
        "name": "network_flap",
        "titles": [
            "Intermittent connectivity drops",
            "DNS resolution failures",
            "BGP route flap detected",
            "VPN tunnel instability",
            "Load balancer health check failures",
        ],
        "descriptions": [
            "Network interface on host reporting intermittent packet loss; services affected.",
            "Internal DNS resolver returning NXDOMAIN for known-good service names.",
            "BGP route advertisement withdrawn and re-announced repeatedly; traffic black-holed.",
            "Site-to-site VPN tunnel dropping every ~10 minutes; cross-region calls failing.",
            "Load balancer marking healthy backends as down due to health check timeouts.",
        ],
        "severities": ["medium", "high", "critical", "high", "medium"],
        "sources": ["monitoring", "on-call", "security"],
    },
    {
        "name": "security_alerts",
        "titles": [
            "Unusual login location detected",
            "Port scan from external IP",
            "Secrets exposed in logs",
            "Privilege escalation attempt",
            "Brute-force on admin endpoint",
        ],
        "descriptions": [
            "User account logged in from unrecognized country; potential credential compromise.",
            "External IP conducting systematic port scan on production subnet.",
            "API key accidentally logged in plaintext; token rotation required immediately.",
            "Service account attempted to assume IAM role outside permitted boundaries.",
            "Repeated failed login attempts against /admin; rate limiting triggered.",
        ],
        "severities": ["high", "medium", "critical", "critical", "high"],
        "sources": ["security", "monitoring"],
    },
]

NOW = datetime.now(tz=timezone.utc)
RECENT_CUTOFF = NOW - timedelta(days=7)
OLDER_CUTOFF = NOW - timedelta(days=30)


def _random_timestamp() -> datetime:
    """60% of rows in last 7 days, 40% in days 8-30."""
    if random.random() < 0.6:
        delta = timedelta(seconds=random.randint(0, int(timedelta(days=7).total_seconds())))
        return NOW - delta
    else:
        start = timedelta(days=8).total_seconds()
        end = timedelta(days=30).total_seconds()
        delta = timedelta(seconds=random.randint(int(start), int(end)))
        return NOW - delta


def generate() -> pd.DataFrame:
    """Generate 500 synthetic incident rows across 8 risk themes."""
    rows = []
    # Distribute 500 rows across themes (not perfectly equal to look natural)
    theme_counts = [65, 65, 60, 60, 60, 65, 65, 60]  # sums to 500

    i = 1
    for theme, count in zip(THEMES, theme_counts):
        for _ in range(count):
            title_idx = random.randrange(len(theme["titles"]))
            desc_idx = random.randrange(len(theme["descriptions"]))
            sev_idx = random.randrange(len(theme["severities"]))
            source = random.choice(theme["sources"])

            rows.append(
                {
                    "id": f"INC-{i:04d}",
                    "timestamp": _random_timestamp().isoformat(),
                    "title": theme["titles"][title_idx],
                    "description": theme["descriptions"][desc_idx],
                    "severity": theme["severities"][sev_idx],
                    "source": source,
                }
            )
            i += 1

    # Shuffle to mix themes
    random.shuffle(rows)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate()
    out_path = Path(__file__).parent / "incidents.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
