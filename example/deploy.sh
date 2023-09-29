#!/bin/bash

PORT=${1:-ttyUSB0}
PORT=${PORT#/dev/}

if ! command -v mpfshell &> /dev/null
then
    echo "mpfshell could not be found"
    exit 1
fi

echo "Uploading files to $PORT..."
mpfshell --reset --open $PORT --script setup.txt
