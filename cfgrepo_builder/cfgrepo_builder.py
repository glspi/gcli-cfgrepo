import os, sys
import traceback
import asyncio
from pathlib import Path
from typing import Dict
import importlib

import typer
import yaml
from scrapli import AsyncScrapli
from scrapli_cfg import AsyncScrapliCfg

app = typer.Typer(name="cfgrepo - config repo get/loader.")

def load_yaml(filename):
    try:
        with open(filename) as _:
            return yaml.load(_, Loader=yaml.SafeLoader)
    except:
        print("Invalid device file!")
        sys.exit(0)


@app.command("getcfg", help="Pull config from switch, put in 'repo'")
def getcfg(inventory: str):
    print("getcfg")
    DEVICE_INVENTORY = load_yaml(inventory)
    DEVICES = build_device_list(DEVICE_INVENTORY)
    coroutines = [get_configs(device, DEVICE_INVENTORY) for device in DEVICES]
    asyncio.run(async_main(coroutines))
    print("Pulled Configs Successfully.")


@app.command("setcfg", help="Push configs in 'repo' onto switches.")
def setcfg(inventory: str):
    DEVICE_INVENTORY = load_yaml(inventory)
    print("setcfg")
    DEVICE_CONFIGS = build_device_config_tuple_list("configs/", DEVICE_INVENTORY)
    coroutines = [load_configs(device_config) for device_config in DEVICE_CONFIGS]
    asyncio.run(async_main(coroutines))
    print("Loaded Configs Successfully.")


def create_scrapli_device(DEVICE_INVENTORY, device):
    credentialsgroup = device.get("credentials")
    group = credentialsgroup or "default"
    temp =  {
        "host": device["ip"],
        "port": device.get("port") or 22,
        "auth_username": DEVICE_INVENTORY["credentials"][group]["username"],
        "auth_password": DEVICE_INVENTORY["credentials"][group]["password"],
        "auth_strict_key": False,
        "transport": "asyncssh",
        "platform": device["platform"]
        }
    if device.get("transport") == "legacy":
        temp["transport_options"] = {
            "asyncssh": {
                "encryption_algs": ["aes128-cbc", "aes192-cbc", "aes256-ctr", "aes192-ctr"],
                "kex_algs": ["diffie-hellman-group-exchange-sha1"]#, "aes192-cbc", "aes256-ctr", "aes192-ctr"]
            }
        }    
    return temp


def build_device_list(DEVICE_INVENTORY):
    DEVICES = []
    for hostname, device in DEVICE_INVENTORY["devices"].items():
        DEVICES.append(create_scrapli_device(DEVICE_INVENTORY, device))

    return DEVICES


def build_device_config_tuple_list(configs_path, DEVICE_INVENTORY):
    DEVICES = []
    files = Path(configs_path).glob("*")
    for cfg_file in files:
        hostname = str(cfg_file).replace(configs_path, "")
        for name, device in DEVICE_INVENTORY["devices"].items():
            if hostname == name:                
                print(f"reading {cfg_file}")
                with open(cfg_file, "r") as f:
                    config = f.read()

                newdevice = create_scrapli_device(DEVICE_INVENTORY, device)
                DEVICES.append((newdevice, config))
    return DEVICES


def create_file(host, config, DEVICE_INVENTORY):
    os.makedirs("configs/", exist_ok=True)
    for hostname, device in DEVICE_INVENTORY["devices"].items():
        if host == device["ip"]:
            with open("configs/" + hostname, "w") as f:
                f.write(config)
            print(f"got {hostname}")


async def load_configs(device_config):
    device = device_config[0]
    config = device_config[1]
    try:
        async with AsyncScrapli(**device) as conn:
            conn.timeout_ops = 120
            conn.timeout_transport = 0
            cfg_conn = AsyncScrapliCfg(conn=conn, dedicated_connection=True)
            await cfg_conn.prepare()
            await cfg_conn.load_config(config=config, replace=True)
            #diff = await cfg_conn.diff_config()
            #print(diff.side_by_side_diff)
            await cfg_conn.commit_config()

    except scrapli.exceptions.ScrapliTimeout as e:
        #print(e)
        print(f"Timeout on connection to {device['host']}.")

    except Exception as e:
        print(e)
        traceback.print_exc()
        print("\nCatch me better!!\n")
        print(type(e).__name__)


async def get_configs(device, DEVICE_INVENTORY):
    try:
        async with AsyncScrapli(**device) as conn:
            cfg_conn = AsyncScrapliCfg(conn=conn)
            await cfg_conn.prepare()
            config = await cfg_conn.get_config(source="running")
            create_file(conn.host, config.result, DEVICE_INVENTORY)

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

