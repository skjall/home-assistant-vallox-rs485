# vallox-rs485-protocol

The wire protocol of Vallox ventilation units that speak RS485, as a package
of its own. It builds and reads the six-byte telegrams, converts the NTC
temperature table, encodes fan levels and validates setpoints. It opens no
serial port and imports no Home Assistant, so it can be read, audited and
tested without either.

```python
from vallox_rs485_protocol import create_read_request, ValloxTelegram, REG_FAN_SPEED

request = create_read_request(REG_FAN_SPEED)
request.to_bytes()  # b'\x01\x22\x11\x00\x29\x5d'

reply = ValloxTelegram.from_bytes(b"\x01\x11\x22\x29\x0f\x6b")
reply.register, reply.value
```

A telegram is `SYSTEM, SENDER, RECIPIENT, VARIABLE, DATA, CHECKSUM`. A read
request carries `VARIABLE = 0x00` and puts the register it asks about in
`DATA` — the reply comes back with the register in `VARIABLE`.

How each register and each byte offset was established is recorded in
[docs/PROTOCOL.md](https://github.com/skjall/home-assistant-vallox-rs485/blob/main/docs/PROTOCOL.md)
of the integration repository. Change one, change the other.

## Installation

```bash
pip install vallox-rs485-protocol
```

The Home Assistant integration pins this package with `==`, and release-please
raises the pin and the version here in one commit.

## License

MIT
