#!/usr/bin/env python3

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from os import getenv, path, system

import click
import httpx
from tabulate import tabulate

###############################################################################
# Paths


def SPLUNK_HOME(edition):
    return "/usr/local/{}".format("splunk" if edition == "se" else "splunkforwarder")


SRC_DIR = "src"
SPLUNK_ENTERPRISE_DIR = path.join(SRC_DIR, "s14e")
UNIVERSAL_FORWARDER_DIR = path.join(SRC_DIR, "u16f")
LOAD_BALANCER_DIR = path.join(SRC_DIR, "l10r")
DEFAULT_CONFIG_PATH = path.join(SRC_DIR, "config.json")
USER_CONFIG_PATH = "user-config.json"

# End Paths section
###############################################################################

###############################################################################
# Constants

VAGRANT_PROVIDER = getenv("VAGRANT_DEFAULT_PROVIDER", "virtualbox")
BASE_IP = "192.168.56."
PR_INSTANCES_IP_RANGE = {"idx": 2, "sh": 1, "fwd": 3}
INSTANCES_DESCRIPTIONS = {
    "idx": "IDX",
    "sh": "SH",
    "fwd": "UF",
    "hf": "HF",
    "lb": "PR SH LB",
    "manager": "Manager",
}
CLUSTERS_CONFIG = {
    "pr_idx": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "PR",
        "dir": SPLUNK_ENTERPRISE_DIR,
        "edition": "se",
    },
    "pr_sh": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "PR",
        "dir": SPLUNK_ENTERPRISE_DIR,
        "edition": "se",
    },
    "manager": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "",
        "dir": SPLUNK_ENTERPRISE_DIR,
        "edition": "se",
    },
    "de_sh": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "DE",
        "dir": SPLUNK_ENTERPRISE_DIR,
        "edition": "se",
    },
    "de_idx": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "DE",
        "dir": SPLUNK_ENTERPRISE_DIR,
        "edition": "se",
    },
    "lb": {
        "web": lambda ip: f"http://{ip}",
        "env": "",
        "dir": LOAD_BALANCER_DIR,
        "edition": "",
    },
    "fwd": {
        "web": lambda _: "",
        "env": "",
        "dir": UNIVERSAL_FORWARDER_DIR,
        "edition": "uf",
    },
    "hf": {
        "web": lambda _: "",
        "env": "",
        "dir": SPLUNK_ENTERPRISE_DIR,
        "edition": "se",
    },
}

# End Constants section
###############################################################################

###############################################################################
# Helper Functions


def read_default_config():
    try:
        with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def read_user_config():
    try:
        with open(USER_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_config():
    user_config = read_user_config()
    default_config = read_default_config()

    return default_config if user_config == {} else user_config


def write_config(config):
    if not path.exists(USER_CONFIG_PATH):
        config = {**read_default_config(), **config}
    else:
        config = {**read_user_config(), **config}

    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


async def get_splunk_version(ip):
    try:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(
                f"https://{ip}:8089/services/server/info",
                headers={"Authorization": "Basic YWRtaW46YWRtaW4xMjM0"},
            )

        root = ET.fromstring(r.text)

        namespaces = {
            "s": "http://dev.splunk.com/ns/rest",
            "atom": "http://www.w3.org/2005/Atom",
        }

        return root.findall(".//s:key[@name='version']", namespaces)[0].text
    except httpx.ConnectTimeout:
        return "The server is down"
    except httpx.ConnectError:
        return "Can't connect to the server"


# End Helper Functions section
###############################################################################


@click.group()
def cli():
    pass


@cli.command(
    help="Configure base image to create virtual machines. \
Vagrant hub url: https://app.vagrantup.com/boxes/search"
)
@click.argument("image", type=click.STRING, nargs=1, required=True)
def config_base_image(image):
    write_config({"base_config": {"box": image}})

    click.echo(f"\nBase image configured to {image}\n")


@cli.command(help="Configure instances of production indexers")
@click.argument("instances", type=click.IntRange(min=4), nargs=1, required=True)
def config_pr_idx_instances(instances):
    config_instances("pr_idx", instances)


@cli.command(help="Configure instances of production search heads")
@click.argument("instances", type=click.IntRange(min=2), nargs=1, required=True)
def config_pr_sh_instances(instances):
    config_instances("pr_sh", instances)


@cli.command(help="Configure instances of forwarders")
@click.argument("instances", type=click.IntRange(min=1), nargs=1, required=True)
def config_fwd_instances(instances):
    config_instances("fwd", instances)


def config_instances(cluster, instances):
    cluster_name = cluster
    cluster_without_env = cluster_name.replace("pr_", "")
    config_to_add = {
        cluster_name: {
            "nodes": {
                "ips": [
                    f"{BASE_IP}{PR_INSTANCES_IP_RANGE[cluster_without_env]}{n}"
                    for n in range(1, instances + 1)
                ]
            },
        }
    }

    if cluster_name == "pr_idx":
        middle = instances // 2
        config_to_add[cluster_name]["nodes"]["sites"] = [
            "site1" if i <= middle else "site2" for i in range(1, instances + 1)
        ]

    prev_config = get_config()
    prev_nodes_ips = prev_config[cluster_name]["nodes"]["ips"]
    new_nodes_ips = config_to_add[cluster_name]["nodes"]["ips"]
    new_instances_ips = [
        ip
        for ip in config_to_add[cluster_name]["nodes"]["ips"]
        if ip not in prev_nodes_ips
    ]

    write_config(config_to_add)

    instance_description = INSTANCES_DESCRIPTIONS[cluster_without_env]

    if len(new_nodes_ips) > len(prev_nodes_ips):
        click.echo("\nNew instances added to configuration:\n")
        click.echo(
            tabulate(
                [
                    [
                        ip,
                        f"{cluster_name}{ip[-1]}",
                    ]
                    for ip in new_instances_ips
                ],
                headers=["IP", "VM Name"],
                tablefmt="grid",
            )
        )
        click.echo()
    elif len(new_nodes_ips) < len(prev_nodes_ips):
        click.echo(f"\nProduction {instance_description} instances scaled down\n")
    else:
        click.echo(
            f"\nProduction {instance_description} instances already configured.\n"
        )


@cli.command(
    help="""Show information about the architecture.

    - vms: Show information about the virtual machines (IP, virtual machine name, type, \
environment and web interface)"""
)
@click.argument(
    "about", type=click.Choice(["vms"], case_sensitive=False), nargs=1, required=True
)
def info(about):
    def vms():
        config = get_config()
        data = []

        async def get_data_instance(
            cluster_config_key,
            cluster_config_value,
            cluster_key_without_env,
            cluster_edition,
            cluster_env,
            ip,
        ):
            vm_name = (
                f"{cluster_config_key}{ip[-1]}"
                if cluster_env == "PR" or cluster_edition == "uf"
                else cluster_config_key
            )
            version = await get_splunk_version(ip)

            data.append(
                [
                    ip,
                    vm_name,
                    INSTANCES_DESCRIPTIONS[cluster_key_without_env],
                    cluster_env,
                    cluster_config_value["web"](ip),
                    version,
                ]
            )

        async def main():
            async with asyncio.TaskGroup() as tg:
                for cluster_config_key, cluster_config_value in CLUSTERS_CONFIG.items():
                    ips = config[cluster_config_key]["nodes"]["ips"]

                    cluster_key_without_env = cluster_config_key.replace(
                        "pr_", ""
                    ).replace("de_", "")

                    for ip in ips:
                        tg.create_task(
                            get_data_instance(
                                cluster_config_key,
                                cluster_config_value,
                                cluster_key_without_env,
                                cluster_config_value["edition"],
                                cluster_config_value["env"],
                                ip,
                            )
                        )

            click.echo(
                tabulate(
                    data,
                    headers=["IP", "VM Name", "Type", "Env", "Web", "SPL Version"],
                    tablefmt="grid",
                )
            )

        asyncio.run(main())

    switch = {"vms": vms}

    switch[about]()


@cli.command(
    help='Performs actions on the server groups core_pr (manager, production indexers and \
production search heads), core_de (development search head and development indexer), \
fwd (Forwarders), hf (Heavy Forwarder), lb (production search heads load balancer) or \
perform actions in all server groups with argument "all".'
)
@click.option(
    "--action",
    "-a",
    type=click.Choice(["start", "stop", "destroy"], case_sensitive=False),
    help="Action to perform",
)
@click.argument(
    "server_groups",
    type=click.Choice(
        ["core_pr", "core_de", "fwd", "hf", "lb", "all"], case_sensitive=False
    ),
    nargs=-1,
    required=True,
)
def manage(action, server_groups):
    manage_aux(action, server_groups)


def manage_aux(action, server_groups):
    config = get_config()

    pr_idx_nodes_ips = config["pr_idx"]["nodes"]["ips"]
    pr_sh_nodes_ips = config["pr_sh"]["nodes"]["ips"]
    fwd_nodes_ips = config["fwd"]["nodes"]["ips"]

    servers_groups = {
        "core_pr": [
            *[f"pr_idx{ip[-1]}" for ip in pr_idx_nodes_ips],
            *[f"pr_sh{ip[-1]}" for ip in pr_sh_nodes_ips],
        ],
        "core_de": ["de_sh", "de_idx"],
        "fwd": [f"fwd{ip[-1]}" for ip in fwd_nodes_ips],
        "hf": ["hf"],
        "lb": ["lb"],
    }

    dirs = {
        "core_pr": SPLUNK_ENTERPRISE_DIR,
        "core_de": SPLUNK_ENTERPRISE_DIR,
        "hf": SPLUNK_ENTERPRISE_DIR,
        "fwd": UNIVERSAL_FORWARDER_DIR,
        "lb": LOAD_BALANCER_DIR,
    }

    vagrant_actions = {"start": "up", "stop": "halt", "destroy": "destroy"}

    for server_group in server_groups:
        if server_group == "all":
            manage_aux(action, ["core_de", "core_pr", "lb", "hf", "fwd"])
            break

        vagrant_action = vagrant_actions[action]
        vagrant_dir = dirs[server_group]
        servers = servers_groups[server_group]

        if server_group in ["core_pr", "core_de"]:
            command = f"\
cd {vagrant_dir} && \
vagrant --provider={VAGRANT_PROVIDER} {vagrant_action} manager"

            if action == "start":
                splunk_home = SPLUNK_HOME("se")

                command += (
                    f" && vagrant ssh -c '{splunk_home}/bin/splunk start' manager"
                )

            system(command)

        for server in servers:
            command = f"\
cd {vagrant_dir} && \
vagrant --provider={VAGRANT_PROVIDER} {vagrant_action} {server}"

            if action == "start":
                cluster_name = re.sub(r"\d", "", server)

                if cluster_name != "lb":
                    cluster_edition = CLUSTERS_CONFIG[cluster_name]["edition"]
                    splunk_home = SPLUNK_HOME(cluster_edition)

                    command += (
                        f" && vagrant ssh -c '{splunk_home}/bin/splunk start' {server}"
                    )

            system(command)


@cli.command(
    help="""Connect to a virtual machine.

            - vm: Virtual machine name to connect. To see available virtual machines names, use \
the command \"info vms\""""
)
@click.argument("vm", type=click.STRING, nargs=1, required=True)
def connect(vm):
    cluster_name = re.sub(r"\d", "", vm)
    cluster_config = CLUSTERS_CONFIG[cluster_name]
    cluster_dir = cluster_config["dir"]

    system(f"cd {cluster_dir} && vagrant ssh {vm} && cd -")


if __name__ == "__main__":
    cli()
