from http.server import BaseHTTPRequestHandler, HTTPServer
import os


class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message = "<h1>🚀 Nix Infrastructure is Live!</h1><p>The Research Auditor Plumbing is fully connected.</p>"
        self.wfile.write(bytes(message, "utf8"))


def run():
    # Railway provides the PORT environment variable automatically
    port = int(os.environ.get("PORT", 8080))
    # It MUST listen on 0.0.0.0 to be accessible outside the container
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"✅ Web Server started on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
