"""Layar antrian untuk TV lewat jaringan lokal (HTTP).

Buka http://<IP-PC>:<port> di browser TV yang satu jaringan dengan PC. Server hanya mengirim nomor antrian,
nama layanan, video edukasi, dan suara panggilan. Data pasien tidak pernah dikirim ke layar ini.
"""
import json
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import resource_path

MIME = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska",
        ".mov": "video/quicktime", ".avi": "video/x-msvideo", ".wmv": "video/x-ms-wmv"}
SENYAP = (BrokenPipeError, ConnectionError, TimeoutError, OSError)


class Hub:
    """Data bersama antara aplikasi (thread utama) dan server web (thread lain)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {"ready": False}
        self._call = {"seq": 0, "kode": "", "poli": "", "loket": "", "audio": None, "gagal": False}
        self._call_text = ""
        self.videos = {}      # id -> Path (diganti utuh setiap publikasi)
        self.audio_dir = None
        self.chime = None

    def set_state(self, state, videos):
        with self._lock:
            self._state = state
        self.videos = videos

    def new_call(self, t, teks):
        """Nomor baru dipanggil: TV akan membunyikan ting-tung, lalu suara bila audio sudah siap."""
        with self._lock:
            self._call = {"seq": self._call["seq"] + 1, "kode": t["kode"], "poli": t["poli_nama"],
                          "loket": t.get("loket") or "", "audio": None, "gagal": False}
            self._call_text = teks

    def set_audio(self, teks, path):
        with self._lock:
            if teks == self._call_text:
                self._call = {**self._call, "audio": "/audio/" + Path(path).name, "gagal": False}

    def set_failed(self, teks):
        with self._lock:
            if teks == self._call_text and not self._call["audio"]:
                self._call = {**self._call, "gagal": True}

    def snapshot(self):
        with self._lock:
            st, call = dict(self._state), dict(self._call)
        st.update(call=call, epoch=time.time(), tz=time.localtime().tm_gmtoff // 60)
        return st

    @staticmethod
    def html():
        return Path(resource_path("assets/tv.html")).read_bytes()


def lan_addresses():
    """Alamat IPv4 PC di jaringan lokal (yang paling mungkin dipakai TV ditaruh paling depan)."""
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # tidak mengirim paket; hanya memilih antarmuka jaringan
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith(("127.", "169.254.")):
                ips.append(ip)
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith(("127.", "169.254."))]


def make_handler(hub):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "SistemAntrianKlinik"
        timeout = 30

        def log_message(self, *_):
            pass

        def do_GET(self):
            self._route(False)

        def do_HEAD(self):
            self._route(True)

        def _route(self, head):
            path = urlparse(self.path).path
            try:
                if path in ("/", "/tv", "/index.html"):
                    return self._bytes(hub.html(), "text/html; charset=utf-8", head)
                if path == "/api/state":
                    data = json.dumps(hub.snapshot(), ensure_ascii=False).encode("utf-8")
                    return self._bytes(data, "application/json; charset=utf-8", head)
                m = re.fullmatch(r"/video/(\d+)(?:\.\w+)?", path)
                if m:
                    p = hub.videos.get(int(m.group(1)))
                    if p and p.exists():
                        return self._file(p, MIME.get(p.suffix.lower(), "application/octet-stream"), head)
                    return self.send_error(404)
                m = re.fullmatch(r"/audio/([0-9a-f]{20})\.mp3", path)
                if m and hub.audio_dir:
                    p = hub.audio_dir / f"{m.group(1)}.mp3"
                    if p.exists():
                        return self._file(p, "audio/mpeg", head)
                    return self.send_error(404)
                if path == "/chime.wav" and hub.chime and Path(hub.chime).exists():
                    return self._file(Path(hub.chime), "audio/wav", head)
                if path == "/favicon.ico":
                    self.send_response(204)
                    self.send_header("Content-Length", "0")
                    return self.end_headers()
                self.send_error(404)
            except SENYAP:
                pass  # TV menutup koneksi (pindah posisi video, ganti halaman, dll.)

        def _bytes(self, data, ctype, head):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if not head:
                self.wfile.write(data)

        def _file(self, path, ctype, head):
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            rng = self.headers.get("Range")
            if rng:
                m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
                if m and (m.group(1) or m.group(2)):
                    a, b = m.groups()
                    if not a:                       # "bytes=-500": 500 byte terakhir
                        start = max(size - int(b), 0)
                    else:
                        start = int(a)
                        end = min(int(b), size - 1) if b else size - 1
                    if start > end or start >= size:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.send_header("Content-Length", "0")
                        return self.end_headers()
                    status = 206
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if head:
                return
            with open(path, "rb") as f:
                f.seek(start)
                sisa = end - start + 1
                while sisa > 0:
                    chunk = f.read(min(256 * 1024, sisa))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    sisa -= len(chunk)

    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    # Di Windows, SO_REUSEADDR membolehkan dua program memakai port yang sama; matikan agar bentrok port terdeteksi.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, *args, **kwargs):
        self._clients = set()
        self._clients_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def get_request(self):
        sock, addr = super().get_request()
        with self._clients_lock:
            self._clients.add(sock)
        return sock, addr

    def shutdown_request(self, request):
        with self._clients_lock:
            self._clients.discard(request)
        super().shutdown_request(request)

    def close_clients(self):
        """Putuskan semua TV yang masih tersambung (koneksi keep-alive tidak ikut tertutup sendiri)."""
        with self._clients_lock:
            socks, self._clients = list(self._clients), set()
        for s in socks:
            for fn in (lambda: s.shutdown(socket.SHUT_RDWR), s.close):
                try:
                    fn()
                except OSError:
                    pass

    def handle_error(self, request, client_address):
        pass  # TV menutup koneksi di tengah jalan itu hal biasa; jangan cetak jejak error


class WebServer:
    def __init__(self, hub):
        self.hub = hub
        self.httpd = None
        self.thread = None
        self.port = None
        self.ips = []
        self.error = ""

    @property
    def running(self):
        return self.httpd is not None

    def start(self, port=8080):
        """Jalankan server di port ini (atau port kosong berikutnya). True bila berhasil."""
        self.stop()
        self.error = ""
        for p in range(port, port + 10):
            try:
                self.httpd = _Server(("0.0.0.0", p), make_handler(self.hub))
                self.port = p
                break
            except OSError as e:
                self.error = str(e)
        else:
            self.httpd = None
            return False
        self.ips = lan_addresses()
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd.close_clients()
            self.httpd = None

    def urls(self):
        if not self.running:
            return []
        return [f"http://{ip}:{self.port}" for ip in self.ips] or [f"http://localhost:{self.port}"]
