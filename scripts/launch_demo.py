"""Open the dashboard once the local demo server is ready."""
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8765/'


def main():
    print(f'Starting MedRoute X at {URL}', flush=True)
    print('Keep this window open. Press Ctrl+C to stop the demo.', flush=True)
    with subprocess.Popen([sys.executable, '-m', 'medroute.server'], cwd=ROOT) as server:
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    return server.returncode or 1
                try:
                    with urlopen(URL + 'api/state', timeout=1):
                        pass
                except (URLError, TimeoutError):
                    time.sleep(0.25)
                    continue
                if server.poll() is not None:
                    return server.returncode or 1
                if not webbrowser.open(URL):
                    print(f'Open {URL} in your browser.', flush=True)
                return server.wait()
            print(f'The demo did not respond at {URL}.', file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 0
        finally:
            if server.poll() is None:
                server.terminate()


if __name__ == '__main__':
    raise SystemExit(main())
