import asyncio
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

from app import config
from app.models.alert import AlertEvent

logger = logging.getLogger("lynceus.webhooks")

METRIC_LABELS = {
    "cpu_usage": "CPU",
    "ram_usage": "RAM",
    "disk_usage": "Disk",
}


def _detect_format(url: str, configured_format: str) -> str:
    if configured_format in ("discord", "slack", "generic"):
        return configured_format
    if "discord.com/api/webhooks" in url:
        return "discord"
    if "hooks.slack.com" in url:
        return "slack"
    return "generic"


def _build_payload(
    event: AlertEvent,
    target_format: str,
) -> dict:
    label = METRIC_LABELS.get(event.metric, event.metric)
    is_triggered = event.status == "triggered"
    status_label = "TRIGGERED" if is_triggered else "RESOLVED"

    triggered_iso = (
        event.triggered_at.replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if event.triggered_at
        else "N/A"
    )
    resolved_iso = (
        event.resolved_at.replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if event.resolved_at
        else "N/A"
    )

    if target_format == "discord":
        color = 0xEF4444 if is_triggered else 0x10B981
        title = (
            f"{emoji} Alert Triggered: High {label} on {event.server_id}"
            if is_triggered
            else f"{emoji} Alert Resolved: {label} normalized on {event.server_id}"
        )
        fields = [
            {"name": "Server", "value": f"`{event.server_id}`", "inline": True},
            {"name": "Metric", "value": label, "inline": True},
            {
                "name": "Value / Limit",
                "value": f"{event.value:.1f}% / {event.threshold:.1f}%",
                "inline": True,
            },
            {"name": "Triggered At", "value": triggered_iso, "inline": True},
        ]
        if not is_triggered and event.resolved_at:
            fields.append({"name": "Resolved At", "value": resolved_iso, "inline": True})

        return {
            "username": "Lynceus Monitoring",
            "embeds": [
                {
                    "title": title,
                    "color": color,
                    "fields": fields,
                    "footer": {"text": "Lynceus Telemetry System"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }

    elif target_format == "slack":
        color = "#EF4444" if is_triggered else "#10B981"
        header = f"{emoji} *[ALERT {status_label}]* {label} on `{event.server_id}`: {event.value:.1f}% (threshold {event.threshold:.1f}%)"
        fields = [
            {"title": "Server", "value": event.server_id, "short": True},
            {"title": "Metric", "value": label, "short": True},
            {"title": "Value", "value": f"{event.value:.1f}%", "short": True},
            {"title": "Threshold", "value": f"{event.threshold:.1f}%", "short": True},
            {"title": "Triggered At", "value": triggered_iso, "short": True},
        ]
        if not is_triggered and event.resolved_at:
            fields.append({"title": "Resolved At", "value": resolved_iso, "short": True})

        return {
            "text": header,
            "attachments": [
                {
                    "color": color,
                    "fields": fields,
                    "footer": "Lynceus Telemetry System",
                }
            ],
        }

    else:
        return {
            "event": f"alert_{event.status}",
            "serverId": event.server_id,
            "metric": event.metric,
            "metricLabel": label,
            "value": event.value,
            "threshold": event.threshold,
            "status": event.status,
            "triggeredAt": event.triggered_at.replace(tzinfo=timezone.utc).isoformat()
            if event.triggered_at
            else None,
            "resolvedAt": event.resolved_at.replace(tzinfo=timezone.utc).isoformat()
            if event.resolved_at
            else None,
        }


def _send_http_request(url: str, payload: dict) -> tuple[bool, str]:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Lynceus-Telemetry/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            status_code = response.getcode()
            if 200 <= status_code < 300:
                return True, f"HTTP {status_code}"
            return False, f"HTTP {status_code}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


async def dispatch_alert_webhook(event: AlertEvent, url: Optional[str] = None):
    target_url = url or config.WEBHOOK_URL
    if not target_url:
        return

    target_format = _detect_format(target_url, config.WEBHOOK_FORMAT)
    payload = _build_payload(event, target_format)

    success, msg = await asyncio.to_thread(_send_http_request, target_url, payload)
    if not success:
        logger.warning("Failed to dispatch alert webhook to %s: %s", target_url, msg)
    else:
        logger.info("Successfully dispatched alert webhook (%s): %s", target_format, msg)


async def send_test_webhook(url: Optional[str] = None) -> tuple[bool, str]:
    target_url = url or config.WEBHOOK_URL
    if not target_url:
        return False, "No webhook URL configured. Set LYNCEUS_WEBHOOK_URL."

    dummy_event = AlertEvent(
        id=0,
        server_id="test-node",
        metric="cpu_usage",
        value=98.5,
        threshold=90.0,
        status="triggered",
        triggered_at=datetime.now(timezone.utc),
    )

    target_format = _detect_format(target_url, config.WEBHOOK_FORMAT)
    payload = _build_payload(dummy_event, target_format)

    success, msg = await asyncio.to_thread(_send_http_request, target_url, payload)
    return success, msg
