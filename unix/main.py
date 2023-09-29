from aweb import WebApp, jsonify
import adata
import json
import gc, time, random

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

webapp = WebApp()
WS_CLIENTS = set()
sse = None

# FIXME
class Pin(object):
    IN = 0
    OUT = 1
    port = { 
        '4': 0,
        '5': 0
    }
    def __init__(self, number, dir):
        self.number = number
        self.dir = dir

    def __str__(self):
        return "virtual Pin"
    
    def value(self, status=None):
        if status != None:
            self.port[str(self.number)] = status
        return self.port[str(self.number)]


@webapp.route('/', method='GET')
async def index(req, res):
    gc.collect()
    await webapp.sendfile(res, './index.html')


@webapp.route('/js', method='GET')
def test(req, res):
    d = {
        'bar': ('baz', None, 1.0, 2)
    }
    yield from jsonify(res,d)


@webapp.route('/gpio', method='GET')
async def get_gpio(req, res):
    req.parse_qs()
    pin_number = int(req.form.get('number'))
    pin = Pin(pin_number, Pin.IN)
    print('[DEBUG] pin.value(): {}'.format(pin.value()))
    gc.collect()
    await jsonify(res, {'value': pin.value()})


@webapp.route('/gpio', method='POST')
async def set_gpio(req, res):
    await req.read_json_data()
    pin = Pin(int(req.form.get('number')), Pin.OUT)
    value = req.form.get('value')
    if value == 't':
        if pin.value(): pin.value(0)
        else: pin.value(1)
    else:
        pin.value(int(value))
    print('[DEBUG] Pin:{}, value:{}, status:{}'.format(pin,value,pin.value()))
    gc.collect()
    await jsonify(res, {'value': pin.value()})


@webapp.route('/events')
async def events_handler(reader, writer):
    global sse
    from aweb import EventSource
    sse = await EventSource.upgrade(reader,writer)
    while True:
        await asyncio.sleep(2)
        await sse.send(json.dumps({'time':time.gmtime(), 'y':random.getrandbits(8)}))


@webapp.route('/ws')
async def ws_handler(req, writer):
    global WS_CLIENTS
    # upgrade connection to WebSocket
    ws = await webapp.WebSocket.upgrade(req, writer)
    #req.closed = False
    WS_CLIENTS.add(ws)
    for ws_client in WS_CLIENTS:
        await ws_client.send('test')
    print(await ws.recv())
    WS_CLIENTS.discard(ws)


@webapp.route('/network', method='POST')
async def save_network(req, res):
    size = int(req.headers[b'Content-Length'])
    data = await req.reader.read(size)
    form = json.loads(data)
    if not form['essid'] == '':
        updated_config = {}
        for key in ['essid','password','can_start_ap']:
            if key in form:
                updated_config[key] = form[key]
        adata.save_network(**updated_config)
        current_config = adata.get_network()
        gc.collect()
        await jsonify(res, current_config)
    else:
        await jsonify(res, {'error':'empty essid name'}, '418')


def main():
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.start_server(webapp.handle, '0.0.0.0', 3000))
    gc.collect()
    loop.run_forever()

if __name__ == "__main__":
    main()