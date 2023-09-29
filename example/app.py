from web import WebApp, jsonify
import json
import pdata
import gc
import time
from machine import Pin, ADC

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


webapp = WebApp()
sse = None


@webapp.route('/', method='GET')
async def index(req, res):
    print('gc.mem_free(): {}'.format(gc.mem_free()))
    print('gc.mem_alloc(): {}'.format(gc.mem_alloc()))
    gc.collect()
    await webapp.sendfile(res, './index.html')


@webapp.route('/gpio', method='GET')
async def get_gpio(req, res):
    req.parse_qs()
    pin_number = int(req.form.get('number'))
    if pin_number in [0,2,4,5,12,13,14,15,16]:
        pin = Pin(pin_number, Pin.IN)
        gc.collect()
        await jsonify(res, {'value':pin.value()})
    else:
        await jsonify(res, {'error':'wrong pin number'}, '418')


@webapp.route('/gpio', method='POST')
async def set_gpio(req, res):
    await req.read_json_data()
    pin_number = int(req.form.get('number'))
    if pin_number in [0,2,4,5,12,13,14,15,16]:
        pin = Pin(pin_number, Pin.OUT)
        value = req.form.get('value')
        if value == 't':
            if pin.value(): pin.value(0)
            else: pin.value(1)
        else:
            pin.value(int(value))
        print('[DEBUG] Pin:{}, value:{}, status:{}'.format(pin, value, pin.value()))
        gc.collect()
        await jsonify(res, {'value':pin.value()})
    else:
        await jsonify(res, {'error':'wrong pin number'}, '418')


@webapp.route('/events')
async def events_handler(reader, writer):
    global sse
    from web import EventSource
    adc = ADC(0)
    sse = await EventSource.upgrade(reader,writer)
    while True:
        time.sleep_ms(1000)
        adc_val = adc.read()
        await sse.send(json.dumps({'y':adc_val}))


@webapp.route('/network', method='POST')
async def save_network(req, res):
    size = int(req.headers[b'Content-Length'])
    data = await req.reader.read(size)
    form = json.loads(data)
    updated_config = {}
    for key in ['essid','password','can_start_ap']:
        if key in form:
            updated_config[key] = form[key]
    print('updated_config: ',updated_config)
    pdata.save_network(**updated_config)
    current_config = pdata.get_network()
    gc.collect()
    await jsonify(res, current_config)


def main():
    print('main()')
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.start_server(webapp.handle,'0.0.0.0',80))
    gc.collect()
    loop.run_forever()
    

