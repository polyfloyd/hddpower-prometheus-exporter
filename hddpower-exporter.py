#! /usr/bin/env python3

import argparse
import logging
import re
import subprocess
import time

from prometheus_client import Counter, Gauge, start_http_server


error_count_metric = Counter('hddpower_errors', 'The number of errors encountered while attempting to gather information from devices', ['dev'])
hdd_power_state = Gauge('hddpower_state', 'The device power state (0=standby, 1=active/idle, 2=idle, 3=NVcache_spindown, 4=NVcache_spinup)', ['dev'])


def disk_power_state(blockdev):
    result = subprocess.run(['hdparm', '-C', blockdev], capture_output=True)
    out = result.stdout.decode('ascii')
    m = re.findall(r'drive state is:\s+(.+)$', out, re.M)
    if not m:
        raise Exception('could not find state in %s' % out)
    return m[0]


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Prometheus exporter for hdd power state using hdparm')
    parser.add_argument('dev', type=str, nargs='+', help='List of block devices')
    parser.add_argument('--port', type=int, default=9004,
                        help='The port number to bind the Prometheus exporter to')
    args = parser.parse_args()

    start_http_server(args.port)
    logging.info('started prometheus exporter on port %d', args.port)

    # From hdparm.c
    states = {'standby': 0, 'active/idle': 1, 'idle': 2, 'NVcache_spindown': 3, 'NVcache_spinup': 4}
    devices = args.dev

    while True:
        for dev in devices:
            try:
                current_state = disk_power_state(dev)
            except Exception as err:
                error_count_metric.labels(dev=dev).inc()
                logging.error('could not query device %s: %s', dev, err)
                continue
            hdd_power_state.labels(dev=dev).set(states[current_state])
        time.sleep(10)


main()
