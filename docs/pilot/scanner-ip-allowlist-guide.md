# Scanner IP Allowlist Guide

Provide pilot customers the egress IP(s) of the SiberCheck scanner workers for WAF allowlisting.

## Current Deployment

- Production worker host: configure from `deploy/production.env.example` and infrastructure records.
- Benchmark/lab: loopback fixtures only (`127.0.0.1:18080`, `127.0.0.1:18081`) — not customer-facing.

## Recommendation

Share outbound NAT IP before first active scan. Update customers when worker IP changes.
