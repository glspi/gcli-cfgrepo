import os, sys
import traceback
import asyncio
from pathlib import Path
from typing import Dict

import typer
from scrapli import AsyncScrapli
from scrapli_cfg import AsyncScrapliCfg

app = typer.Typer(name="cfgrepo - config repo get/loader.")


def grab_device_list(devicemap):
    temp = __import__(devicemap.strip(".py"),globals=globals())
    return temp


@app.command("getcfg", help="Pull config from switch, put in 'repo'")
def getcfg(devicemap: str):
    print("getcfg")
    DEVICE_IP_PORT_MAP = grab_device_list(devicemap)
    DEVICES = build_device_list(DEVICE_IP_PORT_MAP)
    coroutines = [get_configs(device, DEVICE_IP_PORT_MAP) for device in DEVICES]
    asyncio.run(async_main(coroutines))
    print("got em")


@app.command("setcfg", help="Push configs in 'repo' onto switches.")
def setcfg(devicemap: str):
    DEVICE_IP_PORT_MAP = grab_device_list(devicemap)
    print("setcfg")
    DEVICE_CONFIGS = build_device_config_tuple_list("configs/", DEVICE_IP_PORT_MAP)
    coroutines = [load_configs(device_config) for device_config in DEVICE_CONFIGS]
    asyncio.run(async_main(coroutines))
    print("put em")


def build_device_list(DEVICE_IP_PORT_MAP):
    DEVICES = []
    for name, host_port in DEVICE_IP_PORT_MAP.devices.items():
        DEVICES.append(
            {
                "host": host_port[0],
                "port": host_port[1],
                "auth_username": DEVICE_IP_PORT_MAP.username,
                "auth_password": DEVICE_IP_PORT_MAP.password,
                "auth_strict_key": False,
                "transport": "asyncssh",
                "platform": "arista_eos",
            },
        )

    return DEVICES


def build_device_config_tuple_list(configs_path, DEVICE_IP_PORT_MAP):
    DEVICES = []
    files = Path(configs_path).glob("*")
    for cfg_file in files:
        hostname = str(cfg_file).replace(configs_path, "")
        for name, host_port in DEVICE_IP_PORT_MAP.devices.items():
            if hostname == name:
                device = {
                    "host": host_port[0],
                    "port": host_port[1],
                    "auth_username": DEVICE_IP_PORT_MAP.username,
                    "auth_password": DEVICE_IP_PORT_MAP.password,
                    "auth_strict_key": False,
                    "transport": "asyncssh",
                    "platform": "arista_eos",
                }
                print(f"reading {cfg_file}")
                with open(cfg_file, "r") as f:
                    config = f.read()

                DEVICES.append((device, config))
    return DEVICES


def create_file(host, config, DEVICE_IP_PORT_MAP):
    os.makedirs("configs/", exist_ok=True)
    for name, host_port in DEVICE_IP_PORT_MAP.devices.items():
        if host == host_port[0]:
            with open("configs/" + name, "w") as f:
                f.write(config)


async def load_configs(device_config):
    device = device_config[0]
    config = device_config[1]
    try:
        async with AsyncScrapli(**device) as conn:
            cfg_conn = AsyncScrapliCfg(conn=conn)
            await cfg_conn.prepare()
            await cfg_conn.load_config(config=config, replace=True)
            diff = await cfg_conn.diff_config()
            print(diff.side_by_side_diff)
            await cfg_conn.commit_config()

    except Exception as e:
        print(e)
        traceback.print_exc()
        print("\nCatch me better!!\n")
        print(type(e).__name__)


async def get_configs(device, DEVICE_IP_PORT_MAP):
    try:
        async with AsyncScrapli(**device) as conn:

            cfg_conn = AsyncScrapliCfg(conn=conn)
            await cfg_conn.prepare()
            config = await cfg_conn.get_config(source="running")
            create_file(conn.host, config.result, DEVICE_IP_PORT_MAP)

        return config

    except OSError as e:
        print(e)
        print(f"Connection failed to {device['host']}.")

    except Exception as e:
        print(e)
        traceback.print_exc()
        print("\nCatch me better!!\n")
        print(type(e).__name__)


async def async_main(coroutines):
    _ = await asyncio.gather(*coroutines)
    return None


if __name__ == "__main__":
    app()

