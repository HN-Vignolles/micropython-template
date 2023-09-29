#!/usr/bin/env bash

PORT=${1:-/dev/ttyUSB0}

echo "writing firmware to $PORT"

esptool.py --port $PORT erase_flash
esptool.py --port $PORT --baud 115200 write_flash --verify --flash_size=detect 0 firmware/firmware.bin

