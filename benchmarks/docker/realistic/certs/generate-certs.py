#!/usr/bin/env python3
"""Generate deterministic benchmark TLS certificates (run once, commit output)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

OUT = Path(__file__).resolve().parent
NOT_BEFORE = datetime(2026, 1, 1, tzinfo=UTC)
NOT_AFTER = datetime(2036, 1, 1, tzinfo=UTC)
CA_SUBJECT = x509.Name(
    [
        x509.NameAttribute(NameOID.COMMON_NAME, "SIBER Benchmark CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SIBER Benchmark"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "TR"),
    ]
)
SERVER_SUBJECT = x509.Name(
    [
        x509.NameAttribute(NameOID.COMMON_NAME, "benchmark-proxy"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SIBER Benchmark"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "TR"),
    ]
)
SAN = x509.SubjectAlternativeName(
    [
        x509.DNSName("benchmark-juice-proxy"),
        x509.DNSName("benchmark-crapi-proxy"),
        x509.DNSName("localhost"),
    ]
)


def _write_key(path: Path, key) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def _write_cert(path: Path, cert) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def main() -> None:
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(CA_SUBJECT)
        .issuer_name(CA_SUBJECT)
        .public_key(ca_key.public_key())
        .serial_number(1)
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(NOT_AFTER)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(SERVER_SUBJECT)
        .issuer_name(CA_SUBJECT)
        .public_key(server_key.public_key())
        .serial_number(2)
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(NOT_AFTER)
        .add_extension(SAN, critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    _write_key(OUT / "ca.key", ca_key)
    _write_cert(OUT / "ca.crt", ca_cert)
    _write_key(OUT / "server.key", server_key)
    _write_cert(OUT / "server.crt", server_cert)
    print(f"Wrote benchmark certs to {OUT}")


if __name__ == "__main__":
    main()
