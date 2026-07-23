"""Tests for ZAP benchmark allowlist and plugin collapse."""

from __future__ import annotations

from app.benchmark.alert_dedup import (
    collapse_groups_by_plugin_id,
    filter_zap_alerts_by_plugin_allowlist,
    group_zap_alerts,
)
from app.benchmark.zap_allowlist import load_zap_api_active_allowlist, load_zap_web_active_allowlist
from app.analysis.correlation_rules import resolve_correlation_key


def test_web_active_allowlist_matches_subset_plugins():
    allowlist = load_zap_web_active_allowlist()
    assert allowlist == {"10038", "10035", "10021", "10037", "10096"}


def test_api_active_allowlist_excludes_cors_plugin():
    allowlist = load_zap_api_active_allowlist()
    assert "10098" not in allowlist


def test_filter_zap_alerts_drops_out_of_scope_plugins():
    allowlist = frozenset({"10038"})
    alerts = [
        {"pluginId": "10038", "name": "CSP", "url": "https://benchmark-juice-proxy/", "risk": "Medium"},
        {"pluginId": "10098", "name": "CORS", "url": "https://benchmark-juice-proxy/", "risk": "Medium"},
    ]
    filtered = filter_zap_alerts_by_plugin_allowlist(alerts, allowlist)
    assert len(filtered) == 1
    assert filtered[0]["pluginId"] == "10038"


def test_collapse_groups_by_plugin_id_merges_urls():
    alert_a = {"pluginId": "10038", "name": "CSP", "url": "https://benchmark-juice-proxy/a", "risk": "Medium"}
    alert_b = {"pluginId": "10038", "name": "CSP", "url": "https://benchmark-juice-proxy/b", "risk": "Medium"}
    groups = group_zap_alerts([alert_a, alert_b])
    collapsed = collapse_groups_by_plugin_id(groups)
    assert len(collapsed) == 1
    assert collapsed[0].instance_count == 2
    assert len(collapsed[0].child_endpoints) == 2


def test_zap_title_fallback_maps_server_leaks():
    key = resolve_correlation_key(
        "zap",
        "zap-unknown",
        'Server Leaks Version Information via "Server" HTTP Response Header Field',
    )
    assert key == "server-disclosure"
