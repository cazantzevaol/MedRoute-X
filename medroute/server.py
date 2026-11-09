"""Loopback-only synthetic demo dashboard; NOT a production medical service.

Run: python -m medroute.server
Open: http://127.0.0.1:8765
"""
import json
import socket
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from .engine import DisruptionError, Sandbox
from .agents import ROLES
from .review_packet import review_packet
from .learning import save_preference
from .scenario_import import parse_scenario, template
from .scenarios import flagship
from .local_ai import BriefingUnavailable, local_briefing
from .evaluate import evaluate
from .knowledge import search_claims, catalog
from .policy import evidence_dossier
from .council import run_council, OfflineProvider
from .coverage import report as coverage_report

WEB = Path(__file__).resolve().parent.parent / "web"
GAME = Sandbox()
LOCK = Lock()
# A fixed, non-secret header is a browser cross-origin/form guard, not user auth.
DASHBOARD_HEADER = 'dashboard-v1'
MAX_POST_BYTES = 128
MAX_SCENARIO_BYTES = 16384
REQUEST_IDLE_TIMEOUT = 5

class Handler(BaseHTTPRequestHandler):
    timeout = REQUEST_IDLE_TIMEOUT

    def _host_is_local(self):
        # Exact host+port matching defeats common DNS-rebinding attempts.
        # Do not trust Host to select a different origin on a loopback listener.
        port = self.server.server_port
        return self.headers.get('Host', '').lower() in (
            f'127.0.0.1:{port}', f'localhost:{port}'
        )

    def _valid_target(self):
        # Reject absolute-form and protocol-relative request targets.
        return self.path.startswith('/') and not self.path.startswith('//')

    def _check_local_target(self):
        if not self._host_is_local():
            self.reply(b'Unrecognized local Host', 421, 'text/plain; charset=utf-8')
            return False
        if not self._valid_target():
            self.reply(b'Invalid request target', 400, 'text/plain; charset=utf-8')
            return False
        return True

    def reply(self, body, status=200, content_type="application/json; charset=utf-8", *, filename=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-MedRoute-Agent-API", "1")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; "
                         "style-src 'self'; connect-src 'self'; img-src 'self' data:; "
                         "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._check_local_target():
            return
        path = urlsplit(self.path).path
        if path == "/api/review-packet":
            try:
                with LOCK:
                    result = review_packet(GAME)
            except Exception:
                return self.reply(b'{"error":"Could not prepare the review packet."}', 500)
            return self.reply(json.dumps(result).encode())
        if path == "/api/scenario/template":
            return self.reply((json.dumps(template(), indent=2) + "\n").encode(),
                              filename="synthetic-scenario.json")
        if path in ("/api/state", "/api/evaluation", "/api/sources", "/api/dossier", "/api/council", "/api/coverage"):
            if path == "/api/coverage":
                result = coverage_report()
            elif path == "/api/council":
                with LOCK:
                    result = run_council(GAME, provider=OfflineProvider())
            elif path == "/api/sources":
                result = {"catalog": catalog(), "claims": search_claims("medicine supply law international ITU", limit=20)}
            elif path == "/api/dossier":
                with LOCK:
                    result = evidence_dossier(GAME.state())
            else:
                with LOCK:
                    result = GAME.state() if path == "/api/state" else evaluate()
            return self.reply(json.dumps(result, ensure_ascii=False).encode())
        mapping = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
        if path not in mapping: return self.reply(b"Not found", 404, "text/plain")
        media = "text/html" if path == "/" else "application/javascript" if path.endswith(".js") else "text/css"
        return self.reply((WEB/mapping[path]).read_bytes(), content_type=media+"; charset=utf-8")

    def do_POST(self):
        if not self._check_local_target():
            return
        # POST is restricted to same-origin dashboard JavaScript, not arbitrary
        # HTML forms or other websites. The header is not an authentication key.
        origin = self.headers.get('Origin')
        if origin is not None and origin != f"http://{self.headers['Host']}":
            return self.reply(b'Cross-origin write blocked', 403, 'text/plain')
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            return self.reply(b'Cross-site write blocked', 403, 'text/plain')
        if self.headers.get('X-MedRoute-Request') != DASHBOARD_HEADER:
            return self.reply(b'Dashboard request header required', 403, 'text/plain')
        if self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
            return self.reply(b'JSON content type required', 415, 'text/plain')
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get_all('Transfer-Encoding') or len(lengths) != 1:
            return self.reply(b'Invalid request framing', 400, 'text/plain')
        raw_length = lengths[0]
        if not raw_length.isascii() or not raw_length.isdecimal():
            return self.reply(b'Invalid length', 400, 'text/plain')
        path = urlsplit(self.path).path
        limit = MAX_SCENARIO_BYTES if path == '/api/scenario' else 512 if path in ('/api/agents/run', '/api/review-feedback') else MAX_POST_BYTES
        digits = raw_length.lstrip('0')
        if len(digits) > len(str(limit)):
            return self.reply(b'Invalid request length', 413, 'text/plain')
        length = int(digits or '0')
        if not 1 <= length <= limit:
            return self.reply(b'Invalid request length', 413, 'text/plain')
        body = self.rfile.read(length)
        if len(body) != length:
            return self.reply(b'Incomplete request body', 400, 'text/plain')
        try:
            data = json.loads(body)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return self.reply(b'Invalid JSON', 400, 'text/plain')
        if path == '/api/scenario':
            try:
                scenario = parse_scenario(data)
            except ValueError as exc:
                return self.reply(json.dumps({'error': str(exc)}).encode(), 400)
        elif path == '/api/scenario/disruption':
            if not isinstance(data, dict) or set(data) != {'route_id', 'capacity'}:
                return self.reply(b'{"error":"Expected route_id and capacity."}', 400)
        elif path == '/api/scenario/confirm':
            if not isinstance(data, dict) or set(data) != {'disruption_id'}:
                return self.reply(b'{"error":"Expected disruption_id."}', 400)
        elif path == '/api/review-feedback':
            if (not isinstance(data, dict) or set(data) != {'audit_head', 'method', 'useful'}
                    or type(data['useful']) is not bool):
                return self.reply(b'{"error":"Expected audit_head, method and boolean useful."}', 400)
            with LOCK:
                packet = review_packet(GAME)
                if data['audit_head'] != packet['audit_head'] or data['method'] != packet['recommendation']['method']:
                    return self.reply(b'{"error":"Proposal changed. Refresh before rating."}', 409)
                try:
                    save_preference(packet['learning_context'], data['method'], data['useful'])
                except (sqlite3.Error, OSError):
                    return self.reply(b'{"error":"Local feedback storage is unavailable. Your rating was not saved."}', 503)
            return self.reply(b'{"saved":true}')
        elif path == '/api/agents/run':
            roles = data.get('roles') if isinstance(data, dict) else None
            if (not isinstance(data, dict) or set(data) != {'roles'}
                    or not isinstance(roles, list) or not 1 <= len(roles) <= len(ROLES)
                    or any(type(role) is not str or role not in ROLES for role in roles)
                    or len(set(roles)) != len(roles)):
                return self.reply(b'{"error":"Select one or more distinct supported roles."}', 400)
        elif data != {} or not isinstance(data, dict):
            return self.reply(b'Unexpected request payload', 400, 'text/plain')
        if path == '/api/ai/briefing':
            with LOCK:
                state = GAME.state()
            try:
                result = local_briefing(state)
            except BriefingUnavailable as exc:
                return self.reply(json.dumps({'error': str(exc)}).encode(), 503)
            return self.reply(json.dumps(result).encode())
        actions = {
            "/api/agents/run": lambda: run_council(GAME, provider=OfflineProvider(), roles=roles),
            "/api/step": GAME.advance,
            "/api/reset": GAME.reset,
            "/api/scenario": lambda: GAME.reset(scenario),
            "/api/scenario/example": lambda: GAME.reset(flagship()),
            "/api/scenario/disruption": lambda: GAME.report_disruption(**data),
            "/api/scenario/confirm": lambda: GAME.confirm_disruption(data['disruption_id']),
        }
        if path not in actions:
            return self.reply(b"Not found", 404, "text/plain")
        try:
            with LOCK:
                result = actions[path]()
        except DisruptionError as exc:
            return self.reply(json.dumps({'error': str(exc)}).encode(), 400)
        except Exception as exc:
            self.log_error("Simulation update failed (%s)", type(exc).__name__)
            return self.reply(b'{"error":"Simulation update failed"}', 500)
        return self.reply(json.dumps(result, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        # Never advertise permissive cross-origin access to the local simulator.
        return self.reply(b'CORS preflight not supported', 405, 'text/plain')

class DemoServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


if __name__ == "__main__":
    server = DemoServer(("127.0.0.1", 8765), Handler)
    print("MedRoute X live simulation: http://127.0.0.1:8765")
    server.serve_forever()
