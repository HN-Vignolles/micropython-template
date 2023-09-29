FROM library/ubuntu:latest

RUN apt-get update && apt-get -y install micropython git curl

RUN git clone https://github.com/micropython/micropython

RUN mkdir -p ~/.micropython/lib/ \
    && cp -r micropython/extmod/asyncio ~/.micropython/lib/

COPY . .
