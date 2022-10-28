import argparse
import json
import jsonschema
import logging
import os
import signal
import sys
import threading
import time

import watchdog.connections
import watchdog.monitors
import watchdog.reloader

logger = logging.getLogger(__name__)
stop_signal = threading.Event()


def signal_handler(signal_number: int, frame: object) -> None:
    del frame  # Unused
    logger.debug('Got signal %d', signal_number)
    stop_signal.set()


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logging.basicConfig(
        format='[%(asctime)s] [%(levelname)-8s] %(message)s [%(name)s:%(lineno)d]',
        datefmt='%Y-%m-%dT%M:%H:%SZ',  # ISO 8601
        level=logging.DEBUG)
    logging.Formatter.converter = time.gmtime  # UTC

    parser = argparse.ArgumentParser(prog=__package__,
                                     description='Reload the Home Assistant Speedtest integration when it dies')
    parser.add_argument('--version', action='version', version=watchdog.__version__)
    parser.add_argument('-c', '--config', metavar='<path>', help='Configuration file path')
    args = parser.parse_args()

    config_path = os.path.realpath(args.config) if args.config else os.path.realpath('config.json')  # Current directory
    config = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)

            config_schema_filename = 'config.schema.json'
            config_schema_path = next(
                (
                    path for path in [
                        os.path.join(os.path.dirname(__file__), config_schema_filename),  # In module (preferred)
                        os.path.join(os.getcwd(), 'tools', config_schema_filename)  # Repo location (fallback)
                    ] if os.path.exists(path)),
                '')
            if config_schema_path:
                with open(config_schema_path, 'r', encoding='utf-8') as config_schema_file:
                    config_schema = json.load(config_schema_file)
                    logger.debug('Checking configuration against schema: %s', config_schema_path)
                    try:
                        jsonschema.validate(config, config_schema)
                        logger.debug('Validated configuration file against schema')
                    except jsonschema.ValidationError as exception:
                        sys.exit(f'Invalid configuration file: {config_path}\n\n{exception}')
            else:
                logger.warning('No schema found to validate configuration file against')

            logger.info('Loaded configuration file: %s', config_path)
    except json.JSONDecodeError:
        sys.exit(f'Cannot parse non-JSON configuration file: {config_path}')
    except OSError:
        sys.exit(f'Failed to open configuration file: {config_path}')

    home_assistant_connection = watchdog.connections.HomeAssistantConnection(**config['connections']['home_assistant'])
    if not home_assistant_connection.is_valid():
        sys.exit(f'Invalid Home Assistant connection information in configuration file: {config_path}')
    reloader = watchdog.reloader.IntegrationReloader(home_assistant_connection, config['monitor']['config_entry_id'])
    sensor_name = config['monitor']['sensor_name']
    monitor_type = config['monitor'].get('type', 'rest')  # Optional
    monitor: watchdog.monitors.BaseMonitor
    if monitor_type == 'mqtt':
        try:
            mqtt_connection = watchdog.connections.MqttConnection(**config['connections']['mqtt'])
        except KeyError:
            sys.exit(f'Missing MQTT connection object in configuration file: {config_path}')
        if not mqtt_connection.is_valid():
            sys.exit(f'Invalid MQTT connection information in configuration file: {config_path}')
        monitor = watchdog.monitors.MqttMonitor(reloader, sensor_name, mqtt_connection)
    elif monitor_type == 'rest':
        monitor = watchdog.monitors.RestMonitor(reloader, sensor_name, home_assistant_connection)
    else:
        sys.exit(f'Unsupported monitor type in configuration file: {monitor_type}')

    monitor.run(stop_signal)


if __name__ == '__main__':
    main()
