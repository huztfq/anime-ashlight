"""One-time Google sign-in. Needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (an OAuth "Desktop app" client) in .env.
Opens the browser, you approve, and the refresh token is saved to .env (never printed). Usage: python3 google_auth.py"""
import base64, hashlib, http.server, json, secrets, urllib.parse, urllib.request, webbrowser
from gdrive import SCOPE, env, set_env

e = env()
if not e.get("GOOGLE_CLIENT_ID") or not e.get("GOOGLE_CLIENT_SECRET"):
    raise SystemExit("Put GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first.")

verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
state = secrets.token_urlsafe(16)
got = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        if q.get("state") == state and "code" in q:
            got["code"] = q["code"]
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab.</h2>" if "code" in got else b"<h2>Sign-in failed.</h2>")

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(("127.0.0.1", 0), H)
redirect = f"http://127.0.0.1:{srv.server_port}"
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": e["GOOGLE_CLIENT_ID"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
    "access_type": "offline", "prompt": "consent", "state": state,
    "code_challenge": challenge, "code_challenge_method": "S256"})
print("Opening the browser for Google sign-in...")
webbrowser.open(url)
while "code" not in got:
    srv.handle_request()

data = urllib.parse.urlencode({
    "code": got["code"], "client_id": e["GOOGLE_CLIENT_ID"], "client_secret": e["GOOGLE_CLIENT_SECRET"],
    "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}).encode()
tok = json.loads(urllib.request.urlopen("https://oauth2.googleapis.com/token", data).read())
if "refresh_token" not in tok:
    raise SystemExit("Google did not return a refresh token; run again.")
set_env("GOOGLE_REFRESH_TOKEN", tok["refresh_token"])
print("Saved to .env. Drive uploads are ready.")
