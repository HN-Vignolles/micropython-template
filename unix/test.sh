#!/usr/bin/env bash

#curl main-app:3000/js
curl -sd '{"number":5,"value":"0"}' -X POST main-app:3000/gpio
curl -sd '{"number":5,"value":"1"}' -X POST main-app:3000/gpio
[ "x{\"value\": 1}" = "x$(curl -s main-app:3000/gpio?number=5)" ]

