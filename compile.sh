#!/usr/bin/env bash

MPY_PORT=${MPY_PORT:-esp8266}
BUILD_PATH="build-`echo $MPY_PORT | tr '[:lower:]' '[:upper:]'`_GENERIC"
INAME="micropython-${MPY_PORT}"
echo "platform: ${MPY_PORT}"
echo "build path: ${BUILD_PATH}"

# Build a docker image if not exists
if [[ "x$(docker images -q ${INAME} 2> /dev/null)" = "x" ]]; then
  echo "Building new docker image"
  docker build -t ${INAME} --build-arg MPY_PORT=${MPY_PORT} .
fi

docker create -ti --name micropython ${INAME} bash

mkdir -p firmware

docker cp micropython:/lib/micropython/ports/${MPY_PORT}/${BUILD_PATH}/firmware.bin firmware/
docker rm -f micropython
