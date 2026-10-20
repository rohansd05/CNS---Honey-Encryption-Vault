"""X.509 PKI: issue user certs, verify chain/expiry/EKU (PROJECT-BRIEF.md §10).

Owner: T4 — Parth. Phase 1. Placeholder — export ``PKI``.
Must satisfy ``interfaces.PKIAPI`` (frozen in Phase 0; see ``stubs.StubPKI``).
"""

import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from honeycore.interfaces import PKIAPI, CertInfo, InvalidSignatureError


def generate_ec_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def build_root_ca(cn: str, days: int) -> tuple[bytes, bytes]:
    private_key = generate_ec_key()
    public_key = private_key.public_key()
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


def build_issuing_ca(
    root_cert_pem: bytes, root_key_pem: bytes, cn: str, days: int
) -> tuple[bytes, bytes]:
    root_cert = x509.load_pem_x509_certificate(root_cert_pem)
    root_key = serialization.load_pem_private_key(root_key_pem, password=None)

    private_key = generate_ec_key()
    public_key = private_key.public_key()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    issuer = root_cert.subject

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


def issue_leaf(
    issuer_cert_pem: bytes,
    issuer_key_pem: bytes,
    cn: str,
    public_pem: bytes,
    days: int,
    san_dns: list[str] | None = None,
    san_ip: list[str] | None = None,
    eku_server_auth: bool = False,
    eku_client_auth: bool = False,
    key_usage_digital_signature: bool = True,
    key_usage_key_agreement: bool = True,
) -> bytes:
    issuer_cert = x509.load_pem_x509_certificate(issuer_cert_pem)
    issuer_key = serialization.load_pem_private_key(issuer_key_pem, password=None)
    public_key = serialization.load_pem_public_key(public_pem)

    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days - 1)
            if days <= 0
            else datetime.datetime.now(datetime.UTC)
        )
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=key_usage_digital_signature,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=key_usage_key_agreement,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    )

    sans = []
    if san_dns:
        for dns in san_dns:
            sans.append(x509.DNSName(dns))
    if san_ip:
        import ipaddress

        for ip in san_ip:
            sans.append(x509.IPAddress(ipaddress.ip_address(ip)))
    if sans:
        builder = builder.add_extension(x509.SubjectAlternativeName(sans), critical=False)

    ekus = []
    if eku_server_auth:
        ekus.append(ExtendedKeyUsageOID.SERVER_AUTH)
    if eku_client_auth:
        ekus.append(ExtendedKeyUsageOID.CLIENT_AUTH)
    if ekus:
        builder = builder.add_extension(x509.ExtendedKeyUsage(ekus), critical=False)

    cert = builder.sign(issuer_key, hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.PEM)


class PKI(PKIAPI):
    def issue_user_certificate(
        self,
        username: str,
        public_pem: bytes,
        issuer_cert_pem: bytes,
        issuer_key_pem: bytes,
        days: int = 365,
    ) -> bytes:
        return issue_leaf(
            issuer_cert_pem=issuer_cert_pem,
            issuer_key_pem=issuer_key_pem,
            cn=username,
            public_pem=public_pem,
            days=days,
            eku_client_auth=False,
            eku_server_auth=False,
            key_usage_digital_signature=True,
            key_usage_key_agreement=True,
        )

    def verify_certificate(
        self,
        cert_pem: bytes,
        trusted_ca_pems: list[bytes],
        *,
        expected_cn: str | None = None,
        require_client_auth: bool = False,
        expected_root_cn: str | None = None,
    ) -> CertInfo:
        try:
            if not trusted_ca_pems:
                raise InvalidSignatureError("Trust store is empty.")

            cert = x509.load_pem_x509_certificate(cert_pem)
            trusted_certs = [x509.load_pem_x509_certificate(c) for c in trusted_ca_pems]

            now = datetime.datetime.now(datetime.UTC)

            if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
                raise InvalidSignatureError("Certificate is expired or not yet valid.")

            try:
                cert_bc = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
                if cert_bc.ca:
                    raise InvalidSignatureError(
                        "Certificate is a CA, not an end-entity certificate."
                    )
            except x509.ExtensionNotFound:
                pass

            try:
                subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            except IndexError:
                subject_cn = ""
            if expected_cn is not None and subject_cn != expected_cn:
                raise InvalidSignatureError("CN mismatch.")

            if require_client_auth:
                try:
                    eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
                    if ExtendedKeyUsageOID.CLIENT_AUTH not in eku:
                        raise InvalidSignatureError("Client auth EKU required.")
                except x509.ExtensionNotFound:
                    raise InvalidSignatureError(
                        "Client auth EKU required but no EKU extension found."
                    ) from None

            current = cert
            chain: list[x509.Certificate] = []
            visited_der: set[bytes] = set()

            while True:
                issuer = None
                for t in trusted_certs:
                    if t.subject == current.issuer:
                        try:
                            current.verify_directly_issued_by(t)
                            issuer = t
                            break
                        except Exception:  # noqa: S110
                            pass

                if issuer is None:
                    raise InvalidSignatureError("Chain building failed.")

                issuer_der = issuer.public_bytes(serialization.Encoding.DER)
                if issuer_der in visited_der:
                    raise InvalidSignatureError("Certificate chain cycle detected.")
                visited_der.add(issuer_der)

                chain.append(issuer)

                if now < issuer.not_valid_before_utc or now > issuer.not_valid_after_utc:
                    raise InvalidSignatureError("Issuer certificate is expired or not yet valid.")

                try:
                    bc = issuer.extensions.get_extension_for_class(x509.BasicConstraints).value
                    if not bc.ca:
                        raise InvalidSignatureError("Issuer is not a CA.")
                except x509.ExtensionNotFound:
                    raise InvalidSignatureError("Issuer is missing BasicConstraints.") from None

                try:
                    ku = issuer.extensions.get_extension_for_class(x509.KeyUsage).value
                    if not ku.key_cert_sign:
                        raise InvalidSignatureError(
                            "Issuer KeyUsage lacks certificate signing permission (keyCertSign)."
                        )
                except x509.ExtensionNotFound:
                    raise InvalidSignatureError("Issuer is missing KeyUsage extension.") from None

                is_self_signed = False
                if issuer.issuer == issuer.subject:
                    try:
                        issuer.verify_directly_issued_by(issuer)
                        is_self_signed = True
                    except Exception:  # noqa: S110
                        pass

                if is_self_signed:
                    break

                current = issuer

                if len(chain) > 16:
                    raise InvalidSignatureError("Certificate chain exceeded maximum depth.")

            if not chain:
                raise InvalidSignatureError("Certificate chain is empty.")

            terminus = chain[-1]
            if terminus.issuer != terminus.subject:
                raise InvalidSignatureError("Certificate chain does not terminate at a root CA.")
            try:
                terminus.verify_directly_issued_by(terminus)
            except Exception as exc:
                raise InvalidSignatureError(
                    "Chain terminus is not a valid self-signed root CA."
                ) from exc

            try:
                terminus_cns = terminus.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                terminus_cn = terminus_cns[0].value if terminus_cns else ""
            except Exception:
                terminus_cn = ""

            trusted_roots = [t for t in trusted_certs if t.issuer == t.subject]

            if expected_root_cn is not None:
                if terminus_cn != expected_root_cn:
                    raise InvalidSignatureError(
                        f"Root CA CN mismatch: expected '{expected_root_cn}', got '{terminus_cn}'."
                    )
            elif len(trusted_roots) > 1:
                primary_root = trusted_roots[0]
                if terminus.public_bytes(serialization.Encoding.DER) != primary_root.public_bytes(
                    serialization.Encoding.DER
                ):
                    raise InvalidSignatureError(
                        f"Chain terminated at unintended root CA '{terminus_cn}' "
                        f"(expected primary root anchor)."
                    )

            # Validate CA path-length constraints across the chain (RFC 5280 §4.2.1.9)
            for i, ca in enumerate(chain):
                ca_bc = ca.extensions.get_extension_for_class(x509.BasicConstraints).value
                if ca_bc.path_length is not None:
                    num_intermediates = sum(1 for c in chain[:i] if c.subject != c.issuer)
                    if num_intermediates > ca_bc.path_length:
                        try:
                            ca_cn = ca.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                        except Exception:
                            ca_cn = str(ca.subject)
                        raise InvalidSignatureError(
                            f"Path length constraint violated for CA '{ca_cn}': "
                            f"max {ca_bc.path_length} intermediate certs permitted, "
                            f"but {num_intermediates} found."
                        )

            return self.describe(cert_pem)

        except Exception as e:
            if isinstance(e, InvalidSignatureError):
                raise e
            raise InvalidSignatureError(f"Verification failed: {e}") from e

    def describe(self, cert_pem: bytes) -> CertInfo:
        cert = x509.load_pem_x509_certificate(cert_pem)
        try:
            subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except IndexError:
            subject_cn = ""

        try:
            issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except IndexError:
            issuer_cn = ""

        fingerprint = cert.fingerprint(hashes.SHA256()).hex().lower()

        return CertInfo(
            subject_cn=subject_cn,
            issuer_cn=issuer_cn,
            serial=cert.serial_number,
            not_before=cert.not_valid_before_utc.isoformat(),
            not_after=cert.not_valid_after_utc.isoformat(),
            fingerprint_sha256=fingerprint,
        )
