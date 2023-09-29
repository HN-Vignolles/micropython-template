# Instructions

Follow [this](../README.md) instructions first.

Run `deploy.sh`. This will upload `boot.py`, `main.py` and `app.py` to your board. Press Reset.

# WiFi
## Credentials

The safe way to set your wifi credentials is to upload `config.json` doing:
```bash
mpfshell -n -c "open ttyUSB0; put config.json"
```

Default AP credentials: `esp-A:TempPassword` &nbsp; (c.f. [main.py](main.py) )

## IP

To find the IP of the board:

```bash
# Option 1:
screen /dev/ttyUSB0 115200 # then Reset the board and wait for the info messages (C-a \ to exit)

# Option 2:
nmap -sT -p 80 192.168.1.0/24
```