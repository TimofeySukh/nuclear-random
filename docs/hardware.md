# Hardware

## ESP32-C3 Wiring

- Geiger counter pulse output: GPIO 6
- Edge: falling
- Serial baud: `115200`
- Default Linux serial device: `/dev/ttyACM0`

## Wi-Fi Firmware

Firmware lives in:

```text
firmware/esp32c3_geiger_entropy/esp32c3_geiger_entropy.ino
```

Create local Wi-Fi credentials:

```bash
cp firmware/esp32c3_geiger_entropy/secrets.example.h firmware/esp32c3_geiger_entropy/secrets.h
```

Then edit `secrets.h`:

```cpp
const char *WIFI_SSID = "your-wifi-ssid";
const char *WIFI_PASSWORD = "your-wifi-password";
const char *INGEST_URL = "https://random.datanode.live/v1/entropy/click";
const char *INGEST_TOKEN = "the-server-ingest-token";
```

Build and upload it with USB CDC enabled:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc firmware/esp32c3_geiger_entropy
arduino-cli upload -p /dev/ttyACM0 --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc firmware/esp32c3_geiger_entropy
```

The firmware posts click events over Wi-Fi and also prints JSON lines over USB for debugging:

```json
{"source":"esp32c3_gpio6_wifi","sequence":17,"device_time_us":123456,"dt_us":900000,"total":17,"dropped":0}
```

The API records the server receive timestamp and uses the fractional nanoseconds from that timestamp as the main timing input. The ESP32-provided `micros()` value and inter-click delta are mixed into the same hash.
