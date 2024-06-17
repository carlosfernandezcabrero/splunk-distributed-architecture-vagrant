#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
from os import path
from zipfile import ZipFile

sd = path.dirname(path.abspath(__file__))

subprocess.run(["sh", path.join(sd, "generate_package_for_share.sh")])

with ZipFile(
    path.join("/tmp", "splunk-distributed-architecture-vagrant.zip"), "w"
) as zip_ref:
    zip_ref.write(path.join("/tmp", "splunk-distributed-architecture-vagrant"))
