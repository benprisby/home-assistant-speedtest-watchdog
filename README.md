# Home Assistant Speedtest.net Integration Watchdog

[![python](https://img.shields.io/badge/python-3.10-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
[![mypy: checked](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![code style: yapf](https://img.shields.io/badge/code%20style-yapf-blue)](https://github.com/google/yapf)

## Overview

This is a small application to monitor and reload the
[Home Assistant Speedtest.net integration](https://www.home-assistant.io/integrations/speedtestdotnet/) when it drops
out.

In my own Home Assistant setup, I often noticed this integration getting into bad state, where the sensors would become
unavailable and the only fix was to reload the integration (or, big hammer, restart the server). Numerous issues have
been filed on the GitHub repo, but I've yet to see any traction at time of creating this. Even with its issues, I
like the simpicity of having these network metrics readily available to add to my dashboards by using this integration,
hence why I decided to make a simple workaround for it. Hopefully, it is fixed upstream at some point, though.

## Monitor Types

The application features different monitors for examining the value of one of the Speedtest integration sensors. This
reading is used to determine when the integration needs to be reloaded (when it reports `unavailable`).

### MQTT (Preferred)

This monitor connects to an MQTT broker that the Home Assistant server is integrated with and subscribes to the sensor
value. This provides an event-driven approach to getting sensor value changes.

### REST API

This monitor uses the REST API to periodically poll the Home Assistant server for the sensor value.

## Prerequisites

### MQTT Setup

**NOTE**: If you are not planning on using the MQTT monitor, skip this section.

To monitor one the sensor via MQTT, the
[MQTT Statestream integration](https://www.home-assistant.io/integrations/mqtt_statestream/) must be enabled. In my
_configuration.yaml_, I have (like the example):

```yaml
mqtt_statestream:
  base_topic: homeassistant
  publish_attributes: true
  publish_timestamps: true
```

The Statestream integration relies an [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) to point it
at a [broker](https://www.home-assistant.io/docs/mqtt/broker/). To keep things simple, I use the
[Mosquitto add-on](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md) to run a broker locally on
the Home Assistant server, but the application supports pointing at any arbitrary address.

Setting a username and password for the broker is strongly recommended even for local-only setups, but is not required.

### Home Assistant REST API Setup

To reload the integration (and to read the sensor value if using the REST API monitor), the application uses the
[REST API](https://developers.home-assistant.io/docs/api/rest/). As such, it needs to be enabled. In my
_configuration.yaml_, I have simply:

```yaml
api:
```

Once enabled, create an API token if not already done:

1. Navigate to `<Home Assistant address>/profile` (or click your picture in the bottom-left corner of the web UI)
2. Scroll down to "Long-Lived Access Tokens" near the bottom
3. Click "Create Token"

The resulting token is used in the application configuration file detailed below.

### Integration Entry ID

To reload the integration, the application requires the Speedtest integration's entry ID. A simple way to fetch this is
by SSHing into the Home Assistant server and running the following command:

```shell
cat /config/.storage/core.config_entries | jq -rc '.data.entries[] | select(.domain | contains("speedtestdotnet")) | .entry_id'
```

The resulting ID that prints to the screen is used in the application configuration file detailed below.

## Configuration File

Copy _config.sample.json_ to _config.json_ (which is in the _.gitignore_) and fill in the values.

The file format is a JSON object organized into sections. Each section is a top-level property with an object under it.
Dot notation is used to indicate nested heirarchies (e.g. `a.b` translates to `{"a":{"b":"<value>"}}`).

A schema file has been created inside the _tools_ directory to validate both the _config.sample.json_ and _config.json_
files (if created). A Visual Studio Code settings file has been checked in to enforce this schema against those files
when editing them.

### `connections` Section

| Property                            | Data Type | Description |
| ----------------------------------- | --------- | ----------- |
| `home_assistant.address`            | `string`  | Home Assistant server IP address or hostname (_not_ including the scheme) |
| `home_assistant.port`               | `number`  | Home Assistant server port (optional, default: `8123`) |
| `home_assistant.https`              | `boolean` | Whether to connect to the server using HTTPS (optional, default: `true`) |
| `home_assistant.verify_certificate` | `boolean` | If using HTTPS, whether or not certificate verification should be enforced (optional, default: `true`) |
| `home_assistant.api_token`          | `string`  | Home Assistant REST API token collected above |
| `mqtt.address`                      | `string`  | MQTT broker IP address or hostname |
| `mqtt.port`                         | `number`  | MQTT broker port (optional, default: `1883`) |
| `mqtt.username`                     | `string`  | MQTT broker username if required (optional) |
| `mqtt.password`                     | `string`  | MQTT broker password if required (optional) |

**NOTE**: If not using the MQTT monitor, the `mqtt.*` properties can be omitted.

### `monitor` Section

| Property          | Data Type | Description |
| ----------------- | --------- | ----------- |
| `type`            | `string`  | Monitor type to use (`mqtt` or `rest`) |
| `sensor_name`     | `string`  | Speedtest sensor name to monitor (e.g. `speedtest_download`) |
| `config_entry_id` | `string`  | Speedtest integration entry ID collected above |

## Running

Install the required packages:

```shell
poetry install
```

Run the application:

```shell
poetry run python -m watchdog <arguments>
```

For supported command line arguments, run:

```shell
poetry run python -m watchdog --help
```
