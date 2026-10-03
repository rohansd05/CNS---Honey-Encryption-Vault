"""Caller authentication for the honeychecker (PROJECT-BRIEF.md §10).

Owner: T4 — Parth. Placeholder.

TODO(T4 — Parth): per ``HC_TRANSPORT``
* ``plain``  — no check (local dev only);
* ``mtls``   — verify the client certificate CN == ``HC_ALLOWED_CLIENT_CN``;
* ``signed`` — verify ``X-HV-Cert`` chain (Issuing -> Root), CN, EKU clientAuth,
  ``|now - X-HV-Timestamp| <= 60 s``, nonce replay cache (5 min), and the ECDSA
  ``X-HV-Signature`` over ``METHOD\\nPATH\\nTS\\nNONCE\\nSHA256(body)``.
Expose it as a FastAPI dependency applied to every ``/hc/*`` route except ``/hc/health``.
"""
