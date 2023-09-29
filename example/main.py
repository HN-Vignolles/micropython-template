# based on https://gitlab.com/superfly/dawndoor

# this file runs after boot.py

from app import main
import gc
from pdata import get_network
from network import WLAN, STA_IF, AP_IF
import time

wlan = WLAN(STA_IF)
ap = WLAN(AP_IF)


# from WLAN test @micropython:
def wait_for_connection(wifi, timeout=10):
    while not wifi.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
    if wifi.isconnected():
        print("Connected!")
    else:
        print("Connection failed!")


# If no network is set, start the access point in order to set one
network_config = get_network()

if not network_config: # or network_config.get('can_start_ap', True):
    print("No network configuration found. Starting AP...")
    ap.active(True)
    ap.config(essid='esp-A', password='TempPassword')
    print("ap.ifconfig: ", ap.ifconfig())

else:
    print("Network configuration found.")
    try:
        if not (wlan.active() and wlan.isconnected()):
            print("Connecting...")
            wlan.active(True)
            wlan.connect(network_config['essid'], network_config['password'])
            wait_for_connection(wlan)
    except Exception as e:
        print(e)

if wlan.active() and wlan.isconnected():
    print("Using STA. Stopping AP...")
    print("wlan.ifconfig: ", wlan.ifconfig())
    ap.active(False)


gc.collect()
main()
