FROM larsks/esp-open-sdk:latest

LABEL maintainer="Nicolas Vignolles <hn.vignolles@gmail.com>"


ARG MPY_PORT
ENV MPY_PORT ${MPY_PORT:-esp8266}


RUN cd /lib && git clone https://github.com/micropython/micropython.git
WORKDIR /lib/micropython


# Add the external dependencies
RUN make -C ports/${MPY_PORT} submodules


# mpy-cross
# Used to pre-compile Python scripts to .mpy files
RUN  make DEBUG=0 -C mpy-cross


# Copy external modules
COPY mod/. ports/${MPY_PORT}/modules


# Build the micropython port
RUN cd ports/${MPY_PORT} && make DEBUG=0
