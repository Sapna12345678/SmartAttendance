import subprocess
import re
import os
import sys


# ============================================================
# SMART ATTENDANCE - CLOUDFLARE QUICK TUNNEL
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

URL_FILE = os.path.join(
    BASE_DIR,
    "cloudflare_url.txt"
)

DJANGO_URL = "http://127.0.0.1:8000"


# ============================================================
# SAVE PUBLIC URL
# ============================================================

def save_cloudflare_url(url):

    try:

        with open(
            URL_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                url.strip()
            )

        print()
        print("=" * 65)
        print("CLOUDFLARE PUBLIC URL")
        print("=" * 65)
        print(url)
        print("=" * 65)
        print()

        print(
            "URL automatically saved to:"
        )

        print(URL_FILE)

        print()

    except OSError as error:

        print(
            "Unable to save Cloudflare URL:",
            error
        )


# ============================================================
# START CLOUDFLARE
# ============================================================

def start_cloudflare():

    print()
    print("=" * 65)
    print("SMART ATTENDANCE - CLOUDFLARE QUICK TUNNEL")
    print("=" * 65)
    print()

    print(
        "Starting Cloudflare Quick Tunnel..."
    )

    print()

    command = [
        "cloudflared",
        "tunnel",
        "--url",
        DJANGO_URL,
    ]

    try:

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    except FileNotFoundError:

        print()
        print(
            "ERROR: cloudflared was not found."
        )

        print(
            "Make sure cloudflared is installed "
            "and available in PATH."
        )

        print()

        sys.exit(1)


    # ========================================================
    # CLOUDFLARE URL PATTERN
    # ========================================================

    pattern = re.compile(
        r"https://[a-zA-Z0-9-]+\.trycloudflare\.com"
    )

    url_found = False


    # ========================================================
    # READ CLOUDFLARE OUTPUT
    # ========================================================

    try:

        for line in process.stdout:

            line = line.strip()

            if line:

                print(line)


            # Search for public URL

            match = pattern.search(line)

            if match:

                public_url = match.group(0)


                # Save only first URL

                if not url_found:

                    url_found = True

                    save_cloudflare_url(
                        public_url
                    )


    except KeyboardInterrupt:

        print()

        print(
            "Stopping Cloudflare..."
        )

        process.terminate()

        try:

            process.wait(
                timeout=5
            )

        except subprocess.TimeoutExpired:

            process.kill()

        print(
            "Cloudflare stopped."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    start_cloudflare()