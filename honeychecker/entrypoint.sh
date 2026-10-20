#!/bin/sh
set -e

PORT="${PORT:-8001}"
HOST="${HOST:-0.0.0.0}"
TRANSPORT="${HC_TRANSPORT:-plain}"

if [ "$TRANSPORT" = "mtls" ]; then
    SERVER_CERT="${HC_SERVER_CERT_PATH:-/pki/out/honeychecker-server.crt}"
    SERVER_KEY="${HC_SERVER_KEY_PATH:-/pki/out/honeychecker-server.key}"
    CA_CERT="${HC_TRUSTED_CA_CERT_PATH:-/pki/out/service-ca.crt}"

    if [ ! -f "$SERVER_CERT" ]; then
        echo "FATAL: mTLS enabled (HC_TRANSPORT=mtls) but server certificate not found at $SERVER_CERT" >&2
        exit 1
    fi
    if [ ! -f "$SERVER_KEY" ]; then
        echo "FATAL: mTLS enabled (HC_TRANSPORT=mtls) but server private key not found at $SERVER_KEY" >&2
        exit 1
    fi
    if [ ! -f "$CA_CERT" ]; then
        echo "FATAL: mTLS enabled (HC_TRANSPORT=mtls) but CA certificate not found at $CA_CERT" >&2
        exit 1
    fi

    echo "Starting Honeychecker with mTLS on ${HOST}:${PORT} (requiring client certificates from ${CA_CERT})..."
    exec uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --ssl-certfile "$SERVER_CERT" \
        --ssl-keyfile "$SERVER_KEY" \
        --ssl-ca-certs "$CA_CERT" \
        --ssl-cert-reqs 2
else
    echo "Starting Honeychecker with ${TRANSPORT} transport on ${HOST}:${PORT}..."
    exec uvicorn app.main:app --host "$HOST" --port "$PORT"
fi
