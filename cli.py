import json
import re
from os import path, system

import click
from tabulate import tabulate

BASE_IP = "192.168.56."
PR_COMPONENTS_IP_RANGE = {"idx": 2, "sh": 1}
COMPONENTS_ABBR = {
    "idx": "Indexer",
    "sh": "Search Head",
    "fwd": "Universal Forwarder",
    "hf": "Heavy Forwarder",
    "lb": "Prod Search Heads Load Balancer",
    "manager": "Manager",
}

################################################################################
# Paths

SPLUNK_ENTERPRISE_DIR = "s14e"
UNIVERSAL_FORWARDER_DIR = "u16f"
LOAD_BALANCER_DIR = "l10r"
DEFAULT_CONFIG_PATH = path.join(SRC_DIR, "config.json")

# End Paths section
################################################################################

COMPONENTS_CONFIG = {
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


################################################################################
# Helper Functions


def read_default_config():
    try:
        with open(DEFAULT_CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


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
    prev_config = read_default_config()
    prev_config.update({"base_config": {"box": image}})

    with open("config.json", "w") as f:
        json.dump(prev_config, f, indent=4)


@cli.command(
    help="Configure number of production component instances. Apply to idx and sh production components."
)
@click.option(
    "--component",
    "-c",
    type=click.Choice(["pr_idx", "pr_sh", "fwd"], case_sensitive=False),
    help="Production component name to be scaled",
)
@click.option(
    "--instances",
    "-i",
    default=2,
    show_default=True,
    type=click.IntRange(min=2),
    help="Number of production instances to be scaled",
)
def config_instances(component, instances):
    component_without_prefix = component.replace("pr_", "")

    config_to_add = {
        component: {
            "ips": [
                f"{BASE_IP}{PR_COMPONENTS_IP_RANGE[component_without_prefix]}{n}"
                for n in range(1, instances + 1)
            ],
        }
    }
    prev_config = read_default_config()
    prev_ips = prev_config.get(component, {}).get("ips", [])
    new_ips = config_to_add[component]["ips"]
    new_instances = [ip for ip in config_to_add[component]["ips"] if ip not in prev_ips]

    prev_config.update(config_to_add)

    with open("config.json", "w") as f:
        json.dump(prev_config, f, indent=4)

    if len(new_ips) > len(prev_ips):
        click.echo("\nNew instances added to configuration:\n")
        click.echo(
            tabulate(
                [
                    [
                        ip,
                        f"{component}{ip[-1]}",
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
            f"\nProduction {COMPONENTS_ABBR[component_without_prefix]} instances scaled down\n"
        )
    else:
        click.echo(
            f"\nProduction {COMPONENTS_ABBR[component_without_prefix]} instances already configured.\n"
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
        config = read_default_config()

        data_to_show = []
        for component, data in config.items():
            component_config = COMPONENTS_CONFIG.get(component, {})

            for ip in data.get("ips", []):
                type = component.replace("pr_", "").replace("de_", "")
                environment = component_config["env"]

                vm_name = (
                    f"{component}{ip[-1]}"
                    if environment == "PR" or type == "fwd"
                    else component
                )

                data_to_show.append(
                    [
                        ip,
                        vm_name,
                        COMPONENTS_ABBR[type],
                        environment,
                        component_config["web"](ip),
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
    help='Performs actions on the components core_pr (manager, production indexers and production search heads), core_de (development search head and development indexer), fwd (Forwarders), hf (Heavy Forwarder), lb (production search heads load balancer) or perform actions in all components with argument "all".'
)
@click.option(
    "--action",
    "-a",
    type=click.Choice(["start", "stop", "destroy"], case_sensitive=False),
    help="Action to perform",
)
@click.argument(
    "components",
    type=click.Choice(
        ["core_pr", "core_de", "fwd", "hf", "lb", "all"], case_sensitive=False
    ),
    nargs=-1,
    required=True,
)
def manage(action, components):
    manage_aux(action, components)


def manage_aux(action, components):
    config = read_default_config()

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

    for component in components:
        if component == "all":
            manage_aux(action, ["core_de", "core_pr", "lb", "hf", "fwd"])
            break

        v_servers_names = " ".join(servers[component])
        vagrant_action = vagrant_actions[action]
        cd_command = f"cd {dir[component]}"
        vagrant_command = f"vagrant {vagrant_action} {v_servers_names}"

        if component == "core_pr":
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
    component = re.sub(r"\d", "", vm)
    component_config = COMPONENTS_CONFIG[component]
    component_dir = component_config["dir"]

    system(f"cd {component_dir} && vagrant ssh {vm} && cd -")


if __name__ == "__main__":
    cli()
