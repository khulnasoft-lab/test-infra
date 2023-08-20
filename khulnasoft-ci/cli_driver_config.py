#!/usr/bin/env python

# Useful for debugging - set to True
dump_responses = False

default_admin_user = "admin"

default_admin_pass = "foobar"

default_system_wait_timeout = 300
default_system_wait_interval = 10

cmd_prefix = "khulnasoft-cli --json "

cli_command_prefix = "kubectl exec khulnasoft-cli -- "

local_url = "http://localhost:8228/v1"

ci_url = "http://e2e-testing-khulnasoft-engine-api:8228/v1"

repositories = [
    "docker.io/hello-world",  # 8 tags
    "docker.io/ndslabs/nagios-nrpe",  # 6 tags
    "docker.io/mborges/fortran",  # 1 tag
]

test_images = [
    "docker.io/alpine:latest",
    "docker.io/amazonlinux:latest",
    "docker.io/debian:10",
    "docker.io/nginx:latest",
    "docker.io/ubuntu:latest",
]

malware_images = ["docker.io/khulnasoft/test_images:alpine_malware_test"]

clean_images = ["docker.io/khulnasoft/test_images:alpine_clean"]

metadata_types = ["manifest", "docker_history", "dockerfile"]

vulnerability_types = ["os", "non-os", "all"]

content_types = [
    "os",
    "files",
    "npm",
    "gem",
    "python",
    "java",
    "binary",
    "go",
    "malware",
    "nuget",
]

subscription_types = [
    "tag_update",
    "policy_eval",
    "vuln_update",
    "repo_update",
    "analysis_update",
]
