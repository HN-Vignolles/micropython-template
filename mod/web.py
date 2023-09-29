# This web server is based on Raoul Snyman's work: 
# https://gitlab.com/superfly/dawndoor (which is based on Picoweb),
# with some additions taken from 
# https://github.com/wybiral/micropython-aioweb by davy wybiral
# Modified by Nicolas Vignolles
#
# Licensed under the MIT license, see LICENSE for details


try:
    import ure as re
except ImportError:
    import re

try:
    import uerrno as errno
except ImportError:
    import errno

try:
    import ujson as json
except ImportError:
    import json

import hashlib
from binascii import b2a_base64
import struct


def unquote_plus(string):
    string = string.replace('+', ' ')
    arr = string.split('%')
    arr2 = [chr(int(part[:2], 16)) + part[2:] for part in arr[1:]]
    return arr[0] + ''.join(arr2)


def parse_qs(string):
    params = {}
    if string:
        pairs = string.split('&')
        for pair in pairs:
            values = [unquote_plus(part) for part in pair.split('=', 1)]
            if len(values) == 1:
                values.append(True)
            if values[0] in params:
                if not isinstance(params[values[0]], list):
                    params[values[0]] = [params[values[0]]]
                params[values[0]].append(values[1])
            else:
                params[values[0]] = values[1]
    return params


def get_mime_type(fname):
    # Provide minimal detection of important file
    # types to keep browsers happy
    if fname.endswith('.html'):
        return 'text/html'
    if fname.endswith('.css'):
        return 'text/css'
    if fname.endswith('.svg'):
        return 'image/svg+xml'
    if fname.endswith('.png'):
        return 'image/png'
    if fname.endswith('.jpg'):
        return 'image/jpeg'
    if fname.endswith('.txt') or fname.endswith('.csv'):
        return 'text/plain'
    return 'application/octet-stream'


async def sendstream(writer, file_):
    buf = bytearray(64)
    while True:
        line = file_.readinto(buf)
        if not line:
            break
        await writer.awrite(buf, 0, line)


async def jsonify(writer, pydict, status='200'):
    await start_response(writer, 'application/json', status)
    status_n = int(status)
    if status_n >=200 and status_n <= 299:
        pydict['ok'] = True
    else:
        pydict['ok'] = False
    await writer.awrite(json.dumps(pydict))


async def start_response(writer, content_type='text/html', status='200', headers=None, version='1.0'):
    await writer.awrite('HTTP/%s %s NA\r\n' % (version,status))
    if content_type:
        await writer.awrite('Content-Type: ')
        await writer.awrite(content_type)
    if not headers:
        await writer.awrite('\r\n\r\n')
        return
    if isinstance(headers, bytes) or isinstance(headers, str):
        await writer.awrite(headers)
    else:
        for k, v in headers.items():
            await writer.awrite(k)
            await writer.awrite(': ')
            await writer.awrite(v)
            await writer.awrite('\r\n')
    await writer.awrite('\r\n')


def http_error(writer, status):
    yield from start_response(writer, status=status)
    yield from writer.awrite(status)


class HTTPRequest(object):

    async def read_json_data(self):
        size = int(self.headers[b'Content-Length'])
        data = await self.reader.read(size)
        form = json.loads(data)
        self.form = form

    async def read_form_data(self):
        size = int(self.headers[b'Content-Length'])
        data = await self.reader.read(size)
        form = parse_qs(data.decode())
        self.form = form

    def parse_qs(self):
        form = parse_qs(self.qs)
        self.form = form


class WebApp(object):

    def __init__(self):
        self.url_map = []
        self.templates_dir = '/templates'
        self.static_dir = '/static'
        self.url_map.append((re.compile('^/(static/.+)'), self.handle_static))
        self.headers_mode = 'parse'

    def parse_headers(self, reader):
        headers = {}
        while True:
            line = yield from reader.readline()
            if line == b'\r\n':
                break
            key, value = line.split(b':', 1)
            headers[key] = value.strip()
        return headers

    def handle(self, reader, writer):
        close = True
        try:
            request_line = yield from reader.readline()
            if request_line == b'':
                yield from writer.aclose()
                return
            req = HTTPRequest()
            request_line = request_line.decode()
            method, path, proto = request_line.split()
            path = path.split('?', 1)
            qs = ''
            if len(path) > 1:
                qs = path[1]
            path = path[0]

            found = False
            for e in self.url_map:
                pattern = e[0]
                handler = e[1]
                extra = {}
                if len(e) > 2:
                    extra = e[2]

                if path == pattern:
                    if extra and extra.get('method'):
                        if extra['method'] == method:
                            found = True
                            break
                    else:
                        found = True
                        break
                elif not isinstance(pattern, str):
                    m = pattern.match(path)
                    if m:
                        req.url_match = m
                        if extra and extra.get('method'):
                            if extra['method'] == method:
                                found = True
                                break
                        else:
                            found = True
                            break

            if not found:
                headers_mode = 'skip'
            else:
                headers_mode = extra.get('headers', self.headers_mode)

            if headers_mode == 'skip':
                while True:
                    line = yield from reader.readline()
                    if line == b'\r\n':
                        break
            elif headers_mode == 'parse':
                req.headers = yield from self.parse_headers(reader)
            else:
                assert headers_mode == 'leave'

            if found:
                req.method = method
                req.path = path
                req.qs = qs
                req.reader = reader
                close = yield from handler(req, writer)
            else:
                yield from self.abort(writer, '404')
        except Exception:
            pass

        if close is not False:
            yield from writer.aclose()

    def abort(self, writer, status):
        yield from start_response(writer, status=status)
        yield from writer.awrite(status + '\r\n')

    def route(self, url, **kwargs):
        def _route(f):
            self.url_map.append((url, f, kwargs))
            return f
        return _route

    def add_url_rule(self, url, func, **kwargs):
        self.url_map.append((url, func, kwargs))

    def sendfile(self, writer, fname, content_type=None, headers=None):
        if not content_type:
            content_type = get_mime_type(fname)
        try:
            with open(fname) as f:
                yield from start_response(writer, content_type, '200', headers)
                yield from sendstream(writer, f)
        except OSError as e:
            if e.args[0] == errno.ENOENT:
                yield from http_error(writer, '404')
            else:
                raise

    def handle_static(self, req, resp):
        fpath = req.url_match.group(1)
        if '..' in fpath:
            yield from http_error(resp, '403')
            return
        yield from self.sendfile(resp, fpath)


class WebSocket:

    HANDSHAKE_KEY = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    
    OP_TYPES = {
        0x0: 'cont',
        0x1: 'text',
        0x2: 'bytes',
        0x8: 'close',
        0x9: 'ping',
        0xa: 'pong',
    }

    @classmethod
    async def upgrade(cls, r, w):
        h = hashlib.sha1(r.headers[b'Sec-WebSocket-Key'])
        h.update(WebSocket.HANDSHAKE_KEY)
        x = b2a_base64(h.digest())[:-1]
        headers = {
            b'Upgrade': b'websocket',
            b'Connection': b'Upgrade',
            b'Sec-WebSocket-Accept': x
        }
        await start_response(w,content_type=None,status='101',headers=headers,version='1.1')
        await w.drain()
        return cls(r, w)

    def __init__(self, r, w):
        self.r = r
        self.w = w
        self.open = True

    async def recv(self):
        r = self.r.reader
        x = await r.read(2)
        if not x or len(x) < 2:
            return None
        out = {}
        op, n = struct.unpack('!BB', x)
        out['fin'] = bool(op & (1 << 7))
        op = op & 0x0f
        if op not in WebSocket.OP_TYPES:
            raise None
        out['type'] = WebSocket.OP_TYPES[op]
        masked = bool(n & (1 << 7))
        n = n & 0x7f
        if n == 126:
            n, = struct.unpack('!H', await r.read(2))
        elif n == 127:
            n, = struct.unpack('!Q', await r.read(8))
        if masked:
            mask = await r.read(4)
        data = await r.read(n)
        if masked:
            data = bytearray(data)
            for i in range(len(data)):
                data[i] ^= mask[i % 4]
            data = bytes(data)
        if out['type'] == 'text':
            data = data.decode()
        out['data'] = data
        return out

    async def send(self, msg):
        if isinstance(msg, str):
            await self._send_op(0x1, msg.encode())
        elif isinstance(msg, bytes):
            await self._send_op(0x2, msg)

    async def _send_op(self, opcode, payload):
        w = self.w
        w.write(bytes([0x80 | opcode]))
        n = len(payload)
        if n < 126:
            w.write(bytes([n]))
        elif n < 65536:
            w.write(struct.pack('!BH', 126, n))
        else:
            w.write(struct.pack('!BQ', 127, n))
        w.write(payload)
        await w.drain()


class EventSource:

    @classmethod
    async def upgrade(cls, r, w):
        w.write(b'HTTP/1.0 200 OK\r\n')
        w.write(b'Content-Type: text/event-stream\r\n')
        w.write(b'Cache-Control: no-cache\r\n')
        w.write(b'Connection: keep-alive\r\n')
        w.write(b'Access-Control-Allow-Origin: *\r\n')
        w.write(b'\r\n')
        await w.drain()
        return cls(r, w)

    def __init__(self, r, w):
        self.r = r
        self.w = w

    async def send(self, msg, id=None, event=None):
        w = self.w
        if id is not None:
            w.write(b'id: {}\r\n'.format(id))
        if event is not None:
            w.write(b'event: {}\r\n'.format(event))
        w.write(b'data: {}\r\n'.format(msg))
        w.write(b'\r\n')
        await w.drain()
