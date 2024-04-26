import json
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
SPLUNK_ENTERPRISE_DIR = "s14e"
UNIVERSAL_FORWARDER_DIR = "u16f"
LOAD_BALANCER_DIR = "l10r"


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
    prev_config = json.load(open("config.json")) if path.exists("config.json") else {}
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
@click.option(
    "--launch",
    "-l",
    is_flag=True,
    show_default=True,
    default=False,
    help="Launch new instances after configuration",
)
def config_instances(component, instances, launch):
    config_to_add = {
        component: {
            "ips": [
                f"{BASE_IP}{PR_COMPONENTS_IP_RANGE[component.replace('pr_', '')]}{n}"
                for n in range(1, instances + 1)
            ],
        }
    }
    try:
        prev_config = json.load(open("config.json"))
    except FileNotFoundError:
        prev_config = {}

    prev_ips = prev_config.get(component, {}).get("ips", [])
    new_instances = [ip for ip in config_to_add[component]["ips"] if ip not in prev_ips]
    prev_config.update(config_to_add)

    with open("config.json", "w") as f:
        json.dump(prev_config, f, indent=4)

    if not new_instances:
        click.echo(
            f"\nProduction {COMPONENTS_ABBR[component.replace('pr_', '')]} instances already configured.\n"
        )
        return

    if len(config_to_add[component]["ips"]) < len(prev_ips):
        click.echo(
            f"\nProduction {COMPONENTS_ABBR[component.replace('pr_', '')]} instances scaled down. The scale must be do manually.\n"
        )
        return

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

    if launch and new_instances:
        dir = UNIVERSAL_FORWARDER_DIR if component == "fwd" else SPLUNK_ENTERPRISE_DIR
        vms = " ".join([f"{component}{ip[-1]}" for ip in new_instances])

        system(f"cd {dir} && vagrant up {vms} && cd -")


@cli.command(help="Show architecture configuration")
@click.option(
    "--config",
    "-c",
    type=click.Choice(["ips"], case_sensitive=False),
    help="Configuration to show",
)
def show_config(config):
    def ips():
        try:
            config = json.load(open("config.json"))
        except FileNotFoundError:
            config = {}

        data_to_show = []

        for component, data in config.items():
            for ip in data.get("ips", []):
                type = component.replace("pr_", "").replace("de_", "")

                environment = component.split("_")[0]
                environment = "" if environment == type else environment
                environment = "PR" if environment == "pr" else environment
                environment = "DE" if environment == "de" else environment

                vm_name = (
                    f"{component}{ip[-1]}"
                    if environment == "Production" or type == "fwd"
                    else component
                )

                dir = SPLUNK_ENTERPRISE_DIR
                dir = UNIVERSAL_FORWARDER_DIR if type == "fwd" else dir
                dir = LOAD_BALANCER_DIR if type == "lb" else dir

                cwd = path.dirname(path.realpath(__file__))

                identity_file = path.normpath(
                    f"{cwd}/{dir}/.vagrant/machines/{vm_name}/virtualbox/private_key"
                )

                web = f"http://{ip}:8000"
                web = f"http://{ip}" if type == "lb" else web
                web = "" if type == "hf" or type == "fwd" else web

                data_to_show.append(
                    [
                        ip,
                        vm_name,
                        COMPONENTS_ABBR[type],
                        environment,
                        web,
                        f"ssh -i {identity_file} vagrant@{ip}",
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
                    "SSH connection command",
                ],
                tablefmt="grid",
            )
        )

    switch = {"ips": ips}

    switch[config]()


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
    config = json.load(open("config.json"))

    pr_idx_ips = config["pr_idx"]["ips"]
    pr_sh_ips = config["pr_sh"]["ips"]
    fwd_ips = config["fwd"]["ips"]

    servers = {
        "core_pr": [
            "manager",
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

    for component in components:
        if component == "all":
            manage_aux(action, ["core_de", "core_pr", "lb", "hf", "fwd"])
            break

        v_servers_names = " ".join(servers[component])

        switch = {
            "start": lambda: system(
                f"cd {dir[component]} && vagrant up {v_servers_names} && cd -"
            ),
            "stop": lambda: system(
                f"cd {dir[component]} && vagrant halt {v_servers_names} && cd -"
            ),
            "destroy": lambda: system(
                f"cd {dir[component]} && vagrant destroy {v_servers_names} && cd -"
            ),
        }

        switch[action]()


if __name__ == "__main__":
    cli()
