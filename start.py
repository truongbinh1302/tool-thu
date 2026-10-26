#!/usr/bin/env python3
"""Portable local launcher; runtime data lives outside this source folder."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

if sys.version_info < (3, 11):
    raise SystemExit('Tool Thu can Python 3.11 tro len. Hay cai Python tu python.org.')
from thu import __version__
from thu.runtime import build_id, is_frozen, resource_root
from thu.server import LocalServer

ROOT = resource_root()


def default_dir():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'ToolThu'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/ToolThu'
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'tool-thu'


def local_opener(*handlers):
    # Loopback must not go through a system HTTP proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), *handlers)


def running_info(directory):
    try:
        state = json.loads((directory / 'runtime.json').read_text(encoding='utf-8'))
        port = int(state['port'])
        if not 1024 <= port <= 65535:
            return None
        with local_opener().open(f'http://127.0.0.1:{port}/api/health', timeout=1) as response:
            result = json.load(response)
        expected = hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:20]
        if result.get('app') == 'tool-thu-local' and result.get('instance') == expected:
            return {**result, 'port': port}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def health(directory):
    info = running_info(directory)
    return info['port'] if info else None


@contextmanager
def launch_lock(directory, timeout=20):
    """Serialize open/update/stop; OS releases the lock even after a crash."""
    with (directory / 'launcher.lock').open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise SystemExit('Một lượt mở/dừng khác đang xử lý. Hãy thử lại sau ít giây.')
                time.sleep(.1)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def stop_server(directory, info):
    origin = f"http://127.0.0.1:{info['port']}"
    opener = local_opener(urllib.request.HTTPCookieProcessor())
    with opener.open(origin + '/api/bootstrap', timeout=3) as response:
        bootstrap = json.load(response)
    request = urllib.request.Request(origin + '/api/shutdown', data=b'{}', headers={
        'Content-Type': 'application/json', 'Origin': origin, 'X-Tool-CSRF': bootstrap['csrf']})
    with opener.open(request, timeout=3):
        pass
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        # Wait for old cleanup before a new runtime file is written.
        if not (directory / 'runtime.json').exists() and not (directory / 'starting.lock').exists():
            return
        time.sleep(.1)
    raise SystemExit('Phiên cũ chưa dừng xong. Chưa mở phiên mới; dữ liệu được giữ nguyên. Hãy thử lại.')


def serve(directory, port, expected_build):
    lock = directory / 'starting.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime > 30 and not health(directory):
            lock.unlink(missing_ok=True)
            return serve(directory, port, expected_build)
        raise SystemExit('Một phiên đang khởi động. Hãy mở lại sau ít giây.')
    os.close(fd)
    server = None
    try:
        if health(directory):
            return
        for candidate in range(port, min(port + 10, 65536)):
            try:
                server = LocalServer(('127.0.0.1', candidate), directory, ROOT / 'web')
                break
            except OSError as error:
                if getattr(error, 'winerror', None) not in (10013, 10048) and error.errno not in (48, 98, 10048):
                    raise
        if server is None:
            raise SystemExit('Các cổng local đang bận. Chọn cổng khác bằng --port.')
        server.build = expected_build
        state = {'port': server.server_port, 'pid': os.getpid(), 'version': __version__, 'build': server.build}
        temporary = directory / 'runtime.tmp'
        temporary.write_text(json.dumps(state), encoding='utf-8')
        os.replace(temporary, directory / 'runtime.json')
        print(f'Tool Thư {__version__}: http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.server_close()
            (directory / 'runtime.json').unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def server_command(directory, port):
    """Command that starts the background server: re-run this app/script with --serve."""
    args = ['--serve', '--no-browser', '--data-dir', str(directory), '--port', str(port)]
    if is_frozen():
        # A packaged app's executable is the launcher itself; it takes no -X or script path.
        return [sys.executable, *args]
    return [sys.executable, '-X', 'utf8', str(ROOT / 'start.py'), *args]


def launch(directory, port, expected_build):
    log_path = directory / 'startup.log'
    if log_path.exists() and log_path.stat().st_size > 512 * 1024:
        os.replace(log_path, directory / 'startup.previous.log')
    command = server_command(directory, port)
    flags = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    with log_path.open('ab') as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **flags)
    # Generous: a packaged app's first launch on macOS may be slowed by security scans.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        info = running_info(directory)
        if info and info.get('version') == __version__ and info.get('build') == expected_build:
            return info['port']
        if process.poll() is not None:
            break
        time.sleep(.1)
    hint = '' if is_frozen() else '\nChạy Kiem_tra_Tool_Thu_Windows.bat để xem tình trạng.'
    raise SystemExit(f'Chưa mở được Tool Thư. Xem lỗi tại: {log_path}{hint}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default=os.environ.get('TOOL_THU_DATA_DIR'))
    parser.add_argument('--port', type=int, default=28765)
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--diagnose', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('--port cần nằm trong 1024–65535.')
    directory = Path(args.data_dir).expanduser().resolve() if args.data_dir else default_dir().resolve()
    expected_build = build_id()
    if args.diagnose:
        info = running_info(directory)
        print(json.dumps({'version': __version__, 'python': sys.version.split()[0], 'source': str(ROOT),
                          'data': str(directory), 'running': info,
                          'current': bool(info and info.get('version') == __version__ and info.get('build') == expected_build)},
                         ensure_ascii=False, indent=2))
        return
    directory.mkdir(parents=True, exist_ok=True)
    if args.serve:
        return serve(directory, args.port, expected_build)
    with launch_lock(directory):
        info = running_info(directory)
        if args.stop:
            if info:
                stop_server(directory, info)
            print('Tool Thư đã dừng.', flush=True)
            return
        if info and (info.get('version') != __version__ or info.get('build') != expected_build):
            print(f'Đang chuyển Tool Thư sang bản {__version__}…', flush=True)
            stop_server(directory, info)
            info = None
        port = info['port'] if info else launch(directory, args.port, expected_build)
    url = f'http://127.0.0.1:{port}'
    print(f'Tool Thư {__version__}: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)


def show_alert(message):
    """A packaged app has no terminal window, so surface launcher errors in a dialog."""
    if not is_frozen() or '--serve' in sys.argv:
        return
    try:
        if sys.platform == 'darwin':
            script = 'display alert "Tool Thư" message ' + json.dumps(message) + ' as warning'
            subprocess.run(['osascript', '-e', script], timeout=120, check=False)
        elif os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'Tool Thư', 0x30)
    except Exception:
        pass


if __name__ == '__main__':
    if sys.stdout is None or sys.stderr is None:
        # Windowed builds may start without console streams.
        sys.stdout = sys.stdout or open(os.devnull, 'w', encoding='utf-8')
        sys.stderr = sys.stderr or open(os.devnull, 'w', encoding='utf-8')
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    try:
        main()
    except SystemExit as stop:
        if isinstance(stop.code, str):
            show_alert(stop.code)
        raise
    except Exception as error:
        # Exception values may contain imported personal data; do not log them.
        message = f'Không thể mở/dừng Tool Thư ({type(error).__name__}, errno={getattr(error, "errno", None)}). Kiểm tra quyền thư mục, dung lượng và phiên đang chạy.'
        print(message, file=sys.stderr)
        show_alert(message)
        sys.exit(1)

