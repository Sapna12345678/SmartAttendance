from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone
import ipaddress


# ========================================
# SMART ATTENDANCE CERTIFICATE
# ========================================

# Current laptop Wi-Fi IPv4 address
LOCAL_IP = "10.93.229.160"


# ----------------------------------------
# Create private key
# ----------------------------------------

key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)


# ----------------------------------------
# Certificate information
# ----------------------------------------

subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
    x509.NameAttribute(
        NameOID.STATE_OR_PROVINCE_NAME,
        "Uttar Pradesh"
    ),
    x509.NameAttribute(
        NameOID.LOCALITY_NAME,
        "Lucknow"
    ),
    x509.NameAttribute(
        NameOID.ORGANIZATION_NAME,
        "Smart Attendance"
    ),
    x509.NameAttribute(
        NameOID.COMMON_NAME,
        LOCAL_IP
    ),
])


# ----------------------------------------
# Create certificate
# ----------------------------------------

certificate = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())

    .not_valid_before(
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    .not_valid_after(
        datetime.now(timezone.utc) + timedelta(days=365)
    )

    .add_extension(
        x509.SubjectAlternativeName([
            x509.IPAddress(
                ipaddress.ip_address(LOCAL_IP)
            ),

            x509.IPAddress(
                ipaddress.ip_address("127.0.0.1")
            ),

            x509.DNSName("localhost"),
        ]),
        critical=False,
    )

    .sign(
        key,
        hashes.SHA256()
    )
)


# ----------------------------------------
# Save private key
# ----------------------------------------

with open("key.pem", "wb") as key_file:

    key_file.write(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,

            format=serialization.PrivateFormat.TraditionalOpenSSL,

            encryption_algorithm=serialization.NoEncryption(),
        )
    )


# ----------------------------------------
# Save certificate
# ----------------------------------------

with open("cert.pem", "wb") as cert_file:

    cert_file.write(
        certificate.public_bytes(
            serialization.Encoding.PEM
        )
    )


# ----------------------------------------
# Success message
# ----------------------------------------

print()
print("========================================")
print(" HTTPS CERTIFICATE CREATED")
print("========================================")
print()

print("Created:")
print("  cert.pem")
print("  key.pem")

print()

print("IP Address:")
print(f"  {LOCAL_IP}")

print()

print("HTTPS URL:")
print(f"  https://{LOCAL_IP}:8000")

print()