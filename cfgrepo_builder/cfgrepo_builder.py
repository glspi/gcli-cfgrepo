import os
import traceback
import asyncio
from pathlib import Path

import typer
from scrapli import AsyncScrapli
from scrapli_cfg import AsyncScrapliCfg

# Set to False if running locally, True if running in the container
DOCKER = True

DEVICE_IP_PORT_MAP = {
    "spine1": (
        "172.254.0.11",
        22 if DOCKER else 20122,
    ),
    "spine2": (
        "172.254.0.12",
        22 if DOCKER else 21122,
    )
    # "leaf1": (
    #     "172.254.0.21",
    #     22 if DOCKER else 2221,
    # ),
    # "leaf2": (
    #     "172.254.0.22",
    #     22 if DOCKER else 2222,
    # ),
}

app = typer.Typer(name="cfgrepo - config repo get/loader.")

@app.command("get", help="Pull config from switch, put in 'repo'")
def get():
    print("get_configs")
    DEVICES = build_device_list()
    coroutines = [get_configs(device) for device in DEVICES]
    asyncio.run(async_main(coroutines))
    print("got em")


@app.command("load", help="Push configs in 'repo' onto switches.")
def load():
    print("load_configs")
    DEVICE_CONFIGS = build_device_config_tuple_list("configs/")
    coroutines = [load_configs(device_config) for device_config in DEVICE_CONFIGS]
    asyncio.run(async_main(coroutines))
    print("put em")


def build_device_list():
    DEVICES = []
    for name, host_port in DEVICE_IP_PORT_MAP.items():
        DEVICES.append(
            {
                "host": host_port[0],
                "port": host_port[1],
                "auth_username": "admin",
                "auth_password": "admin",
                "auth_strict_key": False,
                "transport": "asyncssh",
                "platform": "arista_eos",
            },
        )

    return DEVICES


def build_device_config_tuple_list(configs_path):
    DEVICES = []
    files = Path(configs_path).glob("*")
    print("hi")
    for cfg_file in files:
        hostname = str(cfg_file).replace(configs_path, "")
        for name, host_port in DEVICE_IP_PORT_MAP.items():
            if hostname == name:
                device = {
                    "host": host_port[0],
                    "port": host_port[1],
                    "auth_username": "admin",
                    "auth_password": "admin",
                    "auth_strict_key": False,
                    "transport": "asyncssh",
                    "platform": "arista_eos",
                }
                print(f"reading {cfg_file}")
                with open(cfg_file, "r") as f:
                    config = f.read()

                DEVICES.append((device, config))
    return DEVICES


def create_file(host, config):
    os.makedirs("configs/", exist_ok=True)
    for name, host_port in DEVICE_IP_PORT_MAP.items():
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


async def get_configs(device):
    try:
        async with AsyncScrapli(**device) as conn:

            cfg_conn = AsyncScrapliCfg(conn=conn)
            await cfg_conn.prepare()
            config = await cfg_conn.get_config(source="running")
            create_file(conn.host, config.result)

        return config

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

