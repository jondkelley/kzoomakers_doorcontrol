import re

def parse_uhppoted_config(config_file):
    device_pattern = re.compile(r'^(UT\d+-L\d+)\.(\d+)\.name = (.+)$')
    address_pattern = re.compile(r'^(UT\d+-L\d+)\.(\d+)\.address = (\d+\.\d+\.\d+\.\d+):(\d+)$')
    timezone_pattern = re.compile(r'^(UT\d+-L\d+)\.(\d+)\.timezone = (.+)$')

    devices = {}

    with open(config_file, 'r') as file:
        lines = file.readlines()

    current_device = None

    for line in lines:
        device_match = device_pattern.match(line)
        address_match = address_pattern.match(line)
        timezone_match = timezone_pattern.match(line)

        if device_match:
            model, device_id, name = device_match.groups()
            current_device = devices.setdefault(device_id, {"model": model})
            current_device["name"] = name
        elif address_match and current_device:
            _, _, ipaddr, _ = address_match.groups()
            current_device["ipaddr"] = ipaddr
        elif timezone_match and current_device:
            _, _, timezone = timezone_match.groups()
            current_device["timezone"] = timezone

    return {"devices": devices}
