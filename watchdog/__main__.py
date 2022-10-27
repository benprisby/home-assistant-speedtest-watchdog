import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
import typing

import watchdog.integration_reloader
import watchdog.sensor_monitor

logger = logging.getLogger(__name__)
stop_signal = threading.Event()


def signal_handler(signal_number: int, frame: object) -> None:
    del frame  # Unused
    logger.info('Got signal %d', signal_number)
    stop_signal.set()


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s [%(module)s:%(lineno)d]',
                        datefmt='%Y-%m-%dT%M:%H:%SZ',
                        level=logging.DEBUG)
    logging.Formatter.converter = time.gmtime  # UTC

    parser = argparse.ArgumentParser(prog=__package__,
                                     description='Reload the Home Assistant Speedtest integration when it dies')
    parser.add_argument('-c', '--config', metavar='<path>', help='Configuration file path')
    args = parser.parse_args()

    config_path = os.path.realpath(args.config) if args.config else os.path.join(os.getcwd(), 'config.json')
    config = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
            logger.debug('Loaded configuration file: %s', config_path)
    except json.JSONDecodeError:
        sys.exit(f'Invalid configuration file format: {config_path}')
    except OSError:
        sys.exit(f'Failed to open configuration file: {config_path}')

    home_assistant_config: dict[str, typing.Any] = config['home_assistant']

    reloader = watchdog.integration_reloader.IntegrationReloader(
        **{key: value for key, value in home_assistant_config.items() if key != 'sensor_name'})
    monitor = watchdog.sensor_monitor.SensorMonitor(reloader,
                                                    **{'mqtt_' + key: value for key, value in config['mqtt'].items()},
                                                    sensor_name=home_assistant_config['sensor_name'])

    monitor.run(stop_signal)


if __name__ == '__main__':
    main()
