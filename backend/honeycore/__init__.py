"""honeycore — pure Honey Encryption library (no FastAPI/SQLAlchemy; no I/O but model files).

Owner: T1 lead — Nidhi. Contract: interfaces.py (frozen).
Obtain implementations via ``factory.load_honeycore``.

This package deliberately imports nothing eagerly: ``import honeycore.transport`` or
``honeycore.pki`` (e.g. from the honeychecker) must not pull in argon2, the DTE or model
files. Import submodules explicitly (``from honeycore.factory import load_honeycore``).
"""

__all__ = [
    "baseline",
    "cipher",
    "dte",
    "factory",
    "interfaces",
    "kdf",
    "pki",
    "sharing",
    "sigil",
    "stubs",
    "transport",
    "vault",
]
