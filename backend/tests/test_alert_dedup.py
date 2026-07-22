"""Tests for ZAP alert canonical deduplication."""

from __future__ import annotations

from app.benchmark.alert_dedup import group_zap_alerts, zap_alert_fingerprint


def test_same_alert_different_query_order_collapses_to_one_fingerprint():
    base = {
        "pluginId": "10038",
        "name": "Content Security Policy",
        "risk": "Medium",
        "param": "",
        "attack": "",
    }
    a = {**base, "url": "https://benchmark-juice-proxy/path?b=2&a=1"}
    b = {**base, "url": "https://benchmark-juice-proxy/path?a=1&b=2"}
    assert zap_alert_fingerprint(a) == zap_alert_fingerprint(b)
    groups = group_zap_alerts([a, b])
    assert len(groups) == 1
    assert groups[0].instance_count == 2


def test_different_paths_remain_separate():
    alert_a = {"pluginId": "10038", "name": "CSP", "url": "https://benchmark-juice-proxy/a", "risk": "Medium"}
    alert_b = {"pluginId": "10038", "name": "CSP", "url": "https://benchmark-juice-proxy/b", "risk": "Medium"}
    groups = group_zap_alerts([alert_a, alert_b])
    assert len(groups) == 2
