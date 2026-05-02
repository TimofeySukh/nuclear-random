# Hardware

## ESP32-C3 Wiring

- Geiger counter pulse output: GPIO 6
- Edge: falling
- Serial baud: `115200`
- Default Linux serial device: `/dev/ttyACM0`

## Firmware

Firmware lives in:

```text
firmware/esp32c3_geiger_entropy/esp32c3_geiger_entropy.ino
```

The firmware emits JSON lines:

```json
{"type":"pulse","t_us":123456,"dt_us":900000,"total":17}
```

The collector records the host timestamp at read time and uses the fractional nanoseconds from that timestamp as the main timing input.

