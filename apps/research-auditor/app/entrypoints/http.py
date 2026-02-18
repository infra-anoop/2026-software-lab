# app/entrypoints/http.py — HTTP server for health checks and deployment (PORT, 0.0.0.0).
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = b"Research Auditor server is running"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    port = int(os.environ.get("PORT", "8080"))
    httpd = HTTPServer(("0.0.0.0", port), Handler)  # nosec B104 - intentional for container
    print(f"Listening on 0.0.0.0:{port}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
