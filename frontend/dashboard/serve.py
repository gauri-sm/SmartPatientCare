"""
SmartPatientCare - Simple Dashboard Dev Server
Zero-dependency HTTP server using Python standard library.

Usage:
    python serve.py [port]
Default port: 3000
"""

import http.server
import socketserver
import sys
import os

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIRECTORY))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def translate_path(self, path):
        # Support /demo/videos/ URL paths by mapping to gauri/cv_patient_monitoring/demo/videos or frontend videos
        clean_path = path.split('?', 1)[0].split('#', 1)[0]
        if clean_path.startswith("/demo/videos/"):
            rel = clean_path[len("/demo/videos/"):]
            candidate1 = os.path.join(REPO_ROOT, "gauri", "cv_patient_monitoring", "demo", "videos", rel)
            if os.path.exists(candidate1):
                return candidate1
            candidate2 = os.path.join(DIRECTORY, "videos", rel)
            if os.path.exists(candidate2):
                return candidate2
        elif clean_path.startswith("/videos/"):
            rel = clean_path[len("/videos/"):]
            candidate = os.path.join(DIRECTORY, "videos", rel)
            if os.path.exists(candidate):
                return candidate
            candidate2 = os.path.join(REPO_ROOT, "gauri", "cv_patient_monitoring", "demo", "videos", rel)
            if os.path.exists(candidate2):
                return candidate2
        return super().translate_path(path)

    def log_message(self, format, *args):
        # Clean logging format
        print(f"[SmartPatientCare Dashboard] {args[0]} - {args[1]}")

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 60)
        print(f"[SmartPatientCare] Nursing Station Dashboard Server Running")
        print(f"URL: {url}")
        print(f"Directory: {DIRECTORY}")
        print("=" * 60)
        print("Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down dashboard server.")

if __name__ == "__main__":
    main()
