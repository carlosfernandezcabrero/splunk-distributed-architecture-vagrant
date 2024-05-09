#!/usr/bin/env python3

import json
import re
from os import path, system

import click
from tabulate import tabulate

################################################################################
# Paths

SRC_DIR = "src"
SPLUNK_ENTERPRISE_DIR = path.join(SRC_DIR, "s14e")
UNIVERSAL_FORWARDER_DIR = path.join(SRC_DIR, "u16f")
LOAD_BALANCER_DIR = path.join(SRC_DIR, "l10r")
DEFAULT_CONFIG_PATH = path.join(SRC_DIR, "config.json")
USER_CONFIG_PATH = "user-config.json"

# End Paths section
################################################################################

################################################################################
# Constants

BASE_IP = "192.168.56."
PR_INSTANCES_IP_RANGE = {"idx": 2, "sh": 1}
INSTANCES_DESCRIPTIONS = {
    "idx": "Indexer",
    "sh": "Search Head",
    "fwd": "Universal Forwarder",
    "hf": "Heavy Forwarder",
    "lb": "Prod Search Heads Load Balancer",
    "manager": "Manager",
}
CLUSTERS_CONFIG = {
    "pr_idx": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "PR",
        "dir": SPLUNK_ENTERPRISE_DIR,
    },
    "pr_sh": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "PR",
        "dir": SPLUNK_ENTERPRISE_DIR,
    },
    "manager": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "",
        "dir": SPLUNK_ENTERPRISE_DIR,
    },
    "de_sh": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "DE",
        "dir": SPLUNK_ENTERPRISE_DIR,
    },
    "de_idx": {
        "web": lambda ip: f"http://{ip}:8000",
        "env": "DE",
        "dir": SPLUNK_ENTERPRISE_DIR,
    },
    "lb": {
        "web": lambda ip: f"http://{ip}",
        "env": "",
        "dir": LOAD_BALANCER_DIR,
    },
    "fwd": {
        "web": lambda _: "",
        "env": "",
        "dir": UNIVERSAL_FORWARDER_DIR,
    },
    "hf": {
        "web": lambda _: "",
        "env": "",
        "dir": SPLUNK_ENTERPRISE_DIR,
    },
}

# End Constants section
################################################################################

################################################################################
# Helper Functions


def read_default_config():
    try:
        with open(DEFAULT_CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def read_user_config():
    try:
        with open(USER_CONFIG_PATH) as f:
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

    with open(USER_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


# End Helper Functions section
################################################################################


@click.group()
def cli():
    pass


@cli.command(help="Configure base image to create virtual machines")
@click.option(
    "--image",
    "-i",
    help="Base image to be used for virtual machines",
)
def config_base_image(image):
    write_config({"base_config": {"box": image}})

    click.echo(f"\nBase image configured to {image}\n")


@cli.command(
    help="Configure number of production instances. Apply to production indexers and search heads and also to the forwarders."
)
@click.option(
    "--cluster",
    "-c",
    type=click.Choice(["pr_idx", "pr_sh", "fwd"], case_sensitive=False),
    help="Name of the production cluster to scale",
)
@click.option(
    "--instances",
    "-i",
    default=2,
    show_default=True,
    type=click.IntRange(min=2),
    help="Number of production instances to be scaled",
)
def config_instances(cluster_name, instances):
    cluster_without_env = cluster_name.replace("pr_", "")
    config_to_add = {
        cluster_name: {
            "ips": [
                f"{BASE_IP}{PR_INSTANCES_IP_RANGE[cluster_without_env]}{n}"
                for n in range(1, instances + 1)
            ],
        }
    }
    prev_config = get_config()
    prev_ips = prev_config.get(cluster_name, {}).get("ips", [])
    new_ips = config_to_add[cluster_name]["ips"]
    new_instances = [
        ip for ip in config_to_add[cluster_name]["ips"] if ip not in prev_ips
    ]

    write_config(config_to_add)

    if len(new_ips) > len(prev_ips):
        click.echo("\nNew instances added to configuration:\n")
        click.echo(
            tabulate(
                [
                    [
                        ip,
                        f"{cluster_name}{ip[-1]}",
                    ]
                    for ip in new_instances
                ],
                headers=["IP", "VM Name"],
                tablefmt="grid",
            )
        )
        click.echo()
    elif len(new_ips) < len(prev_ips):
        click.echo(
            f"\nProduction {INSTANCES_DESCRIPTIONS[cluster_without_env]} instances scaled down\n"
        )
    else:
        click.echo(
            f"\nProduction {INSTANCES_DESCRIPTIONS[cluster_without_env]} instances already configured.\n"
        )


@cli.command(
    help="""Show information about the architecture.
    
    - vms: Show information about the virtual machines (IP, virtual machine name, type, environment and web interface)"""
)
@click.argument(
    "about",
    type=click.Choice(["vms"], case_sensitive=False),
    nargs=1,
    required=True,
)
def info(about):
    def vms():
        config = get_config()

        data_to_show = []
        for cluster_name, data in config.items():
            cluster_config = CLUSTERS_CONFIG.get(cluster_name, {})

            for ip in data.get("ips", []):
                cluster_name_without_env = cluster_name.replace("pr_", "").replace(
                    "de_", ""
                )
                environment = cluster_config["env"]

                vm_name = (
                    f"{cluster_name}{ip[-1]}"
                    if environment == "PR" or cluster_name_without_env == "fwd"
                    else cluster_name
                )

                data_to_show.append(
                    [
                        ip,
                        vm_name,
                        INSTANCES_DESCRIPTIONS[cluster_name_without_env],
                        environment,
                        cluster_config["web"](ip),
                    ]
                )

        click.echo(
            tabulate(
                data_to_show,
                headers=[
                    "IP",
                    "VM Name",
                    "Type",
                    "Env",
                    "Web",
                ],
                tablefmt="grid",
            )
        )

    switch = {"vms": vms}

    switch[about]()


@cli.command(
    help='Performs actions on the server groups core_pr (manager, production indexers and production search heads), core_de (development search head and development indexer), fwd (Forwarders), hf (Heavy Forwarder), lb (production search heads load balancer) or perform actions in all server groups with argument "all".'
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

    pr_idx_ips = config["pr_idx"]["ips"]
    pr_sh_ips = config["pr_sh"]["ips"]
    fwd_ips = config["fwd"]["ips"]

    servers = {
        "core_pr": [
            *[f"pr_idx{ip[-1]}" for ip in pr_idx_ips],
            *[f"pr_sh{ip[-1]}" for ip in pr_sh_ips],
        ],
        "core_de": ["de_sh", "de_idx"],
        "fwd": [f"fwd{ip[-1]}" for ip in fwd_ips],
        "hf": ["hf"],
        "lb": ["lb"],
    }

    dir = {
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

        v_servers_names = " ".join(servers[server_group])
        vagrant_action = vagrant_actions[action]
        cd_command = f"cd {dir[server_group]}"
        vagrant_command = f"vagrant {vagrant_action} {v_servers_names}"

        if server_group == "core_pr":
            vagrant_command_aux = vagrant_command
            vagrant_command = f"vagrant {vagrant_action} manager"

            if action == "start":
                vagrant_command += " && python check_master_status.py"

            vagrant_command += f" && {vagrant_command_aux}"

        command = f"{cd_command} && {vagrant_command} && cd -"

        system(command)


@cli.command(
    help="""Connect to a virtual machine.
            
            - vm: Virtual machine name to connect. To see available virtual machines names, use the command \"info vms\""""
)
@click.argument("vm", type=click.STRING, nargs=1, required=True)
def connect(vm):
    cluster_name = re.sub(r"\d", "", vm)
    cluster_config = CLUSTERS_CONFIG[cluster_name]
    cluster_dir = cluster_config["dir"]

    system(f"cd {cluster_dir} && vagrant ssh {vm} && cd -")


if __name__ == "__main__":
    cli()
