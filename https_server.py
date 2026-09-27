import os
import ssl
import socket

from wsgiref.simple_server import make_server, WSGIRequestHandler

# ========================================
# SMART ATTENDANCE DJANGO HTTPS SERVER
# ========================================

HOST = "0.0.0.0"
PORT = 8443

# Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from config.wsgi import application


# ----------------------------------------
# Detect laptop Wi-Fi IP
# ----------------------------------------

def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


LOCAL_IP = get_local_ip()


# ----------------------------------------
# Certificate files
# ----------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CERT_FILE = os.path.join(BASE_DIR, "cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "key.pem")


if not os.path.exists(CERT_FILE):
    print()
    print("ERROR: cert.pem not found!")
    print(CERT_FILE)
    input("Press ENTER to exit...")
    raise SystemExit


if not os.path.exists(KEY_FILE):
    print()
    print("ERROR: key.pem not found!")
    print(KEY_FILE)
    input("Press ENTER to exit...")
    raise SystemExit


# ----------------------------------------
# HTTPS WSGI Server
# ----------------------------------------

class HTTPSWSGIServer:

    def __init__(self, host, port):

        self.server = make_server(
            host,
            port,
            application,
            handler_class=WSGIRequestHandler
        )

        context = ssl.SSLContext(
            ssl.PROTOCOL_TLS_SERVER
        )

        context.load_cert_chain(
            certfile=CERT_FILE,
            keyfile=KEY_FILE
        )

        self.server.socket = context.wrap_socket(
            self.server.socket,
            server_side=True
        )

    def serve_forever(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()


# ----------------------------------------
# Start HTTPS Django Server
# ----------------------------------------

try:

    server = HTTPSWSGIServer(
        HOST,
        PORT
    )

    print()
    print("========================================")
    print(" SMART ATTENDANCE DJANGO HTTPS SERVER")
    print("========================================")
    print()

    print("Django HTTPS Server running at:")
    print()
    print(f"https://{LOCAL_IP}:{PORT}")
    print()

    print("Laptop local address:")
    print(f"https://127.0.0.1:{PORT}")
    print()

    print("Phone should use:")
    print(f"https://{LOCAL_IP}:{PORT}")
    print()

    print("========================================")
    print(" DJANGO HTTPS SERVER STARTED")
    print(" KEEP THIS WINDOW OPEN")
    print("========================================")
    print()

    server.serve_forever()

except KeyboardInterrupt:

    print()
    print("Server stopped.")

except Exception as e:

    print()
    print("========================================")
    print(" ERROR STARTING HTTPS DJANGO SERVER")
    print("========================================")
    print()
    print(e)
    print()

finally:

    try:
        server.shutdown()
    except:
        pass