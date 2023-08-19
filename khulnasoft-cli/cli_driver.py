#!/usr/bin/env python

##################################################################
"""
Test KhulnaSoft by exercising various of the khulnasoft-cli commands.

Uses random fake names/emails for things like users and accounts.

Uses static configuration data (see cli_driver.config.py) for things
like which images to test, repositories, admin creds, etc.

Usage
    python cli_driver.py [command]

    command is one of 
      account
      analysis_archive
      evaluate
      event
      image
      image_deletion(
      policy
      registry
      repo
      subscription
      system

    If no command is provided, all of the commands listed are tested.
    
Commands generally break down to multiple sub-commands. For example,
the account command runs the following sub commands:
    - account_add
    - account_del
    - account_disable
    - account_disable
    - account_enable
    - account_get
    - account_list
    - account_user
    - account_whoami

At the end, the results will be logged/printed: number of successful
and failed positive and negative tests. A return code of 0 or 1 is
returned to indicate good/bad, so that it's useful in CI.
"""
##################################################################

import copy
from distutils.util import strtobool
from dotenv import load_dotenv
import json
import logging
import time
import os
import random
import subprocess
import sys

import cli_driver_config as config

from faker import Faker


def assemble_command(context, args):
    user = " --u " + context["user"]
    password = " --p " + context["password"]
    api_url = " --url " + context["api_url"] + " "
    command = cmd_prefix + user + password + api_url + args
    return command


def fake_account_with_user():
    faker = Faker()
    account = {}
    account["account_name"] = faker.name().replace(" ", "")
    account["user"] = faker.user_name()
    account["email"] = faker.email()
    account["passw"] = faker.password()
    return account


def make_logger():
    logger = logging.getLogger("cli_driver")
    logger.setLevel(logging.DEBUG)
    filehandler = logging.FileHandler("cli_driver.log", "w")
    filehandler.setLevel(logging.DEBUG)
    streamhandler = logging.StreamHandler(sys.stdout)
    streamhandler.setLevel(logging.INFO)
    logformat = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    filehandler.setFormatter(logformat)
    streamhandler.setFormatter(logformat)
    logger.addHandler(streamhandler)
    logger.addHandler(filehandler)
    return logger


def dump_response(component, message):
    if config.dump_responses:
        logger.debug("{0} | response: {1}".format(component, message))


def log_explicit_failure(test_type, action, message, exit_on_fail=False):
    if test_type == "positive":
        logger.warning(action + " | failed (positive test) " + message)
        positive_tests["fail"].append("{0} - {1}".format(action, message))
    else:
        logger.warning(action + " | failed (negative (test) " + message)
        negative_tests["fail"].append("{0} - {1}".format(action, message))


def log_results_simple(desired_state, state, test_type, action, message):
    if state == desired_state:
        if test_type == "positive":
            logger.info(action + " | passed (positive test) " + message)
            positive_tests["pass"].append("{0} - {1}".format(action, message))
        else:
            logger.info(action + " | failed (negative (test) " + message)
            negative_tests["fail"].append("{0} - {1}".format(action, message))
    else:
        if test_type == "positive":
            logger.info(action + " | failed (positive test) " + message)
            positive_tests["fail"].append("{0} - {1}".format(action, message))
        else:
            logger.info(action + " | passed (negative test) " + message)
            negative_tests["pass"].append("{0} - {1}".format(action, message))


def log_results_summary():
    logger.info("==============================")
    logger.info("Test Summary")
    if positive_tests["pass"]:
        logger.info("Positive Tests Passed")
        for test in positive_tests["pass"]:
            logger.info("\t{0}".format(test))
    if positive_tests["fail"]:
        logger.info("Positive Tests Failed")
        for test in positive_tests["fail"]:
            logger.info("\t{0}".format(test))
    if negative_tests["pass"]:
        logger.info("Negative Tests Passed")
        for test in negative_tests["pass"]:
            logger.info("\t{0}".format(test))
    if negative_tests["fail"]:
        logger.info("Negative Tests Failed")
        for test in negative_tests["fail"]:
            logger.info("\t{0}".format(test))
    logger.info("{0} total positive tests passed".format(len(positive_tests["pass"])))
    logger.info("{0} total positive tests failed".format(len(positive_tests["fail"])))
    logger.info("{0} total negative tests passed".format(len(negative_tests["pass"])))
    logger.info("{0} total negative tests failed".format(len(negative_tests["fail"])))
    logger.info("==============================")
    if len(positive_tests["fail"]) > 0:
        logger.warning("One or more positive tests failed. Exiting with failure.")
        sys.exit(1)
    if len(negative_tests["fail"]) > 0:
        logger.warning("One or more negative tests failed. Exiting with failure.")
        sys.exit(1)


# Account commands
def account(context):
    """Invoke the account CLI subcommands."""
    logger.info("account | starting subcommands")
    faker = Faker()
    account_name = faker.name().replace(" ", "")
    account_email = faker.email()
    account_add(context, account_name, account_email)
    account_get(context, account_name)
    account_disable(context, account_name)
    account_enable(context, account_name)
    account_del(context, account_name, test_type="negative")
    account_disable(context, account_name)
    account_del(context, account_name)
    account_list(context)
    account_list(context, account_override=True, test_type="negative")
    context = copy.deepcopy(root_context)
    account_user(context)
    context = copy.deepcopy(root_context)
    account_whoami(context)
    logger.info("account | finished subcommands")


def account_add(context, name, email, test_type="positive", log=True):
    """Invoke the account add CLI subcommand."""
    if log:
        logger.info("account_add | starting")
    command = assemble_command(
        context, " account add --email {0} {1}".format(email, name)
    )
    if log:
        logger.debug("account_add | running command {0}".format(command))
    try:
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        state = response.get("state")
        if log:
            log_results_simple(
                "enabled",
                state,
                test_type,
                "account_add",
                "account: {0}; email: {1}; state: {2}".format(name, email, state),
            )
            logger.info("account_add | finished")
    except Exception as e:
        if log:
            log_explicit_failure(
                test_type, "account_add", "failed to add account {0}".format(name)
            )
            logger.error("account_add | error calling khulnasoft-cli: {0}".format(e))


def account_get(context, name, test_type="positive"):
    """Invoke the account get CLI subcommand."""
    logger.info("account_get | starting")
    command = assemble_command(context, " account get {0}".format(name))
    try:
        logger.debug("account_get | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        state = response.get("state")
        log_results_simple(
            "enabled",
            state,
            test_type,
            "account_get",
            "account: {0}; state: {1}".format(name, state),
        )
        logger.info("account_get | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "account_get", "failed to get account {0}".format(name)
        )
        logger.error("account_get | error calling khulnasoft-cli: {0}".format(e))


def account_disable(context, name, test_type="positive"):
    """Invoke the account disable CLI subcommand."""
    logger.info("account_disable | starting")
    command = assemble_command(context, " account disable {0}".format(name))
    try:
        logger.debug("account_disable | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        state = response.get("state")
        log_results_simple(
            "disabled",
            state,
            test_type,
            "account_disable",
            "account: {0}; state: {1}".format(name, state),
        )
        logger.info("account_disable | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "account_disable", "failed to disable account {0}".format(name)
        )
        logger.error("account_disable | error calling khulnasoft-cli: {0}".format(e))


def account_enable(context, name, test_type="positive"):
    """Invoke the account enable CLI subcommand."""
    logger.info("account_enable | starting")
    command = assemble_command(context, " account enable {0}".format(name))
    try:
        logger.debug("account_enable | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        state = response.get("state")
        log_results_simple(
            "enabled",
            state,
            test_type,
            "account_enable",
            "account: {0}; state: {1}".format(name, state),
        )
        logger.info("account_enable | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "account_enable", "failed to enable account {0}".format(name)
        )
        logger.error("account_enable | error calling khulnasoft-cli: {0}".format(e))


def account_del(context, name, test_type="positive"):
    """Invoke the account del CLI subcommand."""
    logger.info("account_del | starting")
    command = assemble_command(context, " account del --dontask {0}".format(name))
    try:
        logger.debug("account_del | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        state = response.get("state")
        log_results_simple(
            "deleting",
            state,
            test_type,
            "account_del",
            "account: {0}; state: {1}".format(name, state),
        )
        logger.info("account_del | finished")
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            response = json.loads(e.stdout)
            if (
                response.get("message")
                == "Invalid account state change requested. Cannot go from state enabled to state deleting"
            ):
                log_results_simple(
                    "deleting",
                    "enabled",
                    test_type,
                    "account_del",
                    "could not delete account: {0}".format(name),
                )
        else:
            log_explicit_failure(
                test_type, "account_del", "failed to delete account {0}".format(name)
            )
            logger.error("account_del | error calling khulnasoft-cli: {0}".format(e))


def account_list(context, account_override=False, test_type="positive"):
    """Invoke the account list CLI subcommand."""
    logger.info("account_list | starting")

    # make a non-admin user, and thus expect `account list` to fail
    # this implies that test_type is "negative"
    if account_override:
        acct = fake_account_with_user()
        account_add(
            context,
            acct["account_name"],
            acct["email"],
            test_type="positive",
            log=False,
        )
        account_user_add(
            context,
            acct["account_name"],
            acct["user"],
            acct["passw"],
            test_type="positive",
            log=False,
        )
        context["user"] = acct["user"]
        context["password"] = acct["passw"]

    command = assemble_command(context, " account list")

    try:
        logger.debug("account_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_accounts = len(response)
        log_results_simple(
            "ok",
            "ok",
            test_type,
            "account_list",
            "{0} accounts found".format(number_accounts),
        )
        logger.info("account_list | finished")
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            response = json.loads(e.stdout)
            logger.warning(f"handling account-list error response: {response}. exception: {e}. May be ok")
            if account_override:
                if response == "Unauthorized" or response.get("httpcode") == 403:
                    log_results_simple(
                        "ok",
                        "notok",
                        "negative",
                        "account_list",
                        "non-admin user could not list accounts",
                    )
                else:
                    log_explicit_failure(
                        test_type, "account_list", "failed to list accounts"
                    )
                    logger.error(
                        "account_list | error calling khulnasoft-cli: {0}".format(e)
                    )
        else:
            log_explicit_failure(test_type, "account_list", "failed to list accounts")
            logger.error("account_list | error calling khulnasoft-cli: {0}".format(e))


def account_user(context, test_type="positive"):
    """Invoke the account user CLI subcommands."""
    logger.info("account_user | starting subcommands")
    account_user_list(context, test_type)
    context = copy.deepcopy(root_context)
    acct = fake_account_with_user()
    account_add(context, acct["account_name"], acct["email"], test_type)
    account_user_add(
        context, acct["account_name"], acct["user"], acct["passw"], test_type
    )
    account_user_del(context, test_type)
    account_user_get(context, test_type)
    account_user_setpassword(context, test_type)
    logger.info("account_user | finished subcommands")


def account_user_list(context, test_type):
    """Invoke the account user list CLI subcommand.

    We execute 4 cases:
    1. Default user list using admin (no --account)
    2. User list for an account without users using admin
    3. User list for an account with users using admin
    4. User list using a non-admin user

    Note: reset the context after calling this function
    ( context = copy.deepcopy(root_context) ).
    """
    logger.info("account_user_list | starting")
    command = assemble_command(context, " account user list")

    # case 1: default user list
    try:
        logger.debug("account_user_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_users = len(response)
        if number_users:
            log_results_simple(
                "ok",
                "ok",
                test_type,
                "account_user_list",
                "{0} users found".format(number_users),
            )
        else:
            # this is unlikely, as the command will fail if the admin user doesn't exist!
            log_results_simple(
                "ok", "notok", "positive", "account_user_list", "no users found"
            )
    except Exception as e:
        log_explicit_failure(
            test_type, "account_user_list", "failed list users w/admin"
        )
        logger.error("account_user_list | error calling khulnasoft-cli: {0}".format(e))

    # case 2: user list for account w/no users
    try:
        # set up - create an account with no users
        faker = Faker()
        account_name = faker.name().replace(" ", "")
        account_email = faker.email()
        account_add(context, account_name, account_email, log=False)
        command = assemble_command(
            context, " account user list --account {0}".format(account_name)
        )
        logger.debug("account_user_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_users = len(response)
        if not number_users:
            # desired result
            log_results_simple(
                "ok", "notok", "negative", "account_user_list", "no users found (good)"
            )
        else:
            # there shouldn't be any users for this account, so this is a failure condition
            log_results_simple(
                "ok",
                "notok",
                "positive",
                "account_user_list",
                "{0} users found".format(number_users),
            )
    except Exception as e:
        log_explicit_failure(
            test_type,
            "account_user_list",
            "failed to list users w/admin for account w/no users",
        )
        logger.error("account_user_list | error calling khulnasoft-cli: {0}".format(e))

    # case 3: user list for account with users
    try:
        # set up - create an account with a user
        acct = fake_account_with_user()
        account_add(
            context,
            acct["account_name"],
            acct["email"],
            test_type="positive",
            log=False,
        )
        account_user_add(
            context,
            acct["account_name"],
            acct["user"],
            acct["passw"],
            test_type="positive",
            log=False,
        )

        command = assemble_command(
            context, " account user list --account {0}".format(acct["account_name"])
        )
        logger.debug("account_user_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_users = len(response)
        if number_users:
            log_results_simple(
                "ok",
                "ok",
                "positive",
                "account_user_list",
                "{0} users found".format(number_users),
            )
        else:
            log_results_simple(
                "ok", "notok", "positive", "account_user_list", "no users found"
            )
    except Exception as e:
        log_explicit_failure(
            test_type,
            "account_user_list",
            "failed to list users w/admin for account w/a user",
        )
        logger.error("account_user_list | error calling khulnasoft-cli: {0}".format(e))

    # case 4: list users in an account, using a non-admin user
    acct = fake_account_with_user()
    account_add(
        context, acct["account_name"], acct["email"], test_type="positive", log=False
    )
    account_user_add(
        context,
        acct["account_name"],
        acct["user"],
        acct["passw"],
        test_type="positive",
        log=False,
    )
    acct = fake_account_with_user()
    context["user"] = acct["user"]
    context["password"] = acct["passw"]

    command = assemble_command(
        context, " account user list --account {0}".format(acct["account_name"])
    )

    try:
        logger.debug("account_user_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_users = len(response)
        # we expect this to throw an exception
        log_results_simple(
            "ok",
            "ok",
            "negative",
            "account_user_list",
            "{0} users found - but should have thrown an exception".format(
                number_users
            ),
        )
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            response = json.loads(e.stdout)
            if response == "Unauthorized" or response.get("httpcode") == 403:
                log_results_simple(
                    "ok",
                    "notok",
                    "negative",
                    "account_user_list",
                    "Non-admin user could not list accounts (good)",
                )
            else:
                logger.error(
                    "account_user_list | error calling khulnasoft-cli: {0}".format(e)
                )
        else:
            log_explicit_failure(
                test_type,
                "account_user_list",
                "failed to list users w/a non admin user",
            )
            logger.error("account_user_list | error calling khulnasoft-cli: {0}".format(e))
    logger.info("account_user_list | finished")


def account_user_add(context, account, username, userpass, test_type, log=True):
    """Invoke the account user add CLI subcommand."""
    if log:
        logger.info("account_user_add | starting")
    command = assemble_command(
        context,
        " account user add --account {0} {1} {2}".format(account, username, userpass),
    )
    if log:
        logger.debug("account_user_add | running command {0}".format(command))
    try:
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        created = response.get("created_at")
        user = response.get("username")
        if log:
            logger.info("account_user_add | finished")
            if created and user:
                log_results_simple(
                    "ok",
                    "ok",
                    "positive",
                    "account_user_add",
                    "user: {0} added at {1}".format(user, created),
                )
            else:
                log_results_simple(
                    "ok",
                    "notok",
                    "positive",
                    "account_user_add",
                    "user not added; json response: {0}".format(response),
                )
    except Exception as e:
        if log:
            log_explicit_failure(
                test_type,
                "account_user_add",
                "failed to add user {0} to account {1}".format(username, account),
            )
            logger.error("account_user_add | error calling khulnasoft-cli: {0}".format(e))


def account_user_del(context, test_type):
    """Invoke the account user add CLI subcommand."""
    logger.info("account_user_del | starting")
    acct = fake_account_with_user()
    account_add(
        context, acct["account_name"], acct["email"], test_type="positive", log=False
    )
    account_user_add(
        context,
        acct["account_name"],
        acct["user"],
        acct["passw"],
        test_type="positive",
        log=False,
    )
    command = assemble_command(
        context,
        " account user del --account {0} {1}".format(
            acct["account_name"], acct["user"]
        ),
    )
    logger.debug("account_user_del | running command {0}".format(command))
    try:
        # as long as this doesn't throw an exception or return 4xx, we're ok
        subprocess.run(command.split(), check=True, stdout=subprocess.PIPE)
        log_results_simple(
            "ok",
            "ok",
            "positive",
            "account_user_del",
            "user {0} deleted from account {1}".format(
                acct["user"], acct["account_name"]
            ),
        )
        logger.info("account_user_del | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "account_user_del", "failed to del user {0}".format(acct["user"])
        )
        logger.error("account_user_del | error calling khulnasoft-cli: {0}".format(e))


def account_user_get(context, test_type):
    """Invoke the account user get CLI subcommand."""
    logger.info("account_user_get | starting")
    acct = fake_account_with_user()
    account_add(
        context, acct["account_name"], acct["email"], test_type="positive", log=False
    )
    account_user_add(
        context,
        acct["account_name"],
        acct["user"],
        acct["passw"],
        test_type="positive",
        log=False,
    )
    command = assemble_command(
        context,
        " account user get --account {0} {1}".format(
            acct["account_name"], acct["user"]
        ),
    )
    logger.debug("account_user_get | running command {0}".format(command))
    try:
        # as long as this doesn't throw an exception or return 4xx, we're ok
        subprocess.run(command.split(), check=True, stdout=subprocess.PIPE)
        log_results_simple(
            "ok",
            "ok",
            "positive",
            "account_user_get",
            "got user {0} from account {1}".format(acct["user"], acct["account_name"]),
        )
        logger.info("account_user_get | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "account_user_get", "failed to get user {0}".format(acct["user"])
        )
        logger.error("account_user_get | error calling khulnasoft-cli: {0}".format(e))


def account_user_setpassword(context, test_type):
    """Invoke the account user setpassword CLI subcommand."""
    logger.info("account_user_setpassword | starting")
    acct = fake_account_with_user()
    account_add(
        context, acct["account_name"], acct["email"], test_type="positive", log=False
    )
    account_user_add(
        context,
        acct["account_name"],
        acct["user"],
        acct["passw"],
        test_type="positive",
        log=False,
    )
    command = assemble_command(
        context,
        " account user setpassword --account {0} --username {1} {2}".format(
            acct["account_name"], acct["user"], acct["passw"]
        ),
    )
    logger.debug("account_user_setpassword | running command {0}".format(command))
    try:
        # as long as this doesn't throw an exception or return 4xx, we're ok
        subprocess.run(command.split(), check=True, stdout=subprocess.PIPE)
        log_results_simple(
            "ok",
            "ok",
            "positive",
            "account_user_setpassword",
            "set password of user {0} from account {1}".format(
                acct["user"], acct["account_name"]
            ),
        )
        logger.info("account_user_setpassword | finished")
    except Exception as e:
        log_explicit_failure(
            test_type,
            "account_user_setpassword",
            "failed to set password of user {0}".format(acct["user"]),
        )
        logger.error(
            "account_user_setpassword | error calling khulnasoft-cli: {0}".format(e)
        )


# /Account user subcommands


def account_whoami(context, test_type="positive"):
    """Invoke the account whoami CLI subcommand."""
    logger.info("account_whoami | starting")
    acct = fake_account_with_user()
    account_add(
        context, acct["account_name"], acct["email"], test_type="positive", log=False
    )
    account_user_add(
        context,
        acct["account_name"],
        acct["user"],
        acct["passw"],
        test_type="positive",
        log=False,
    )
    command = assemble_command(context, " account whoami")
    logger.debug("account_whoami | running command {0}".format(command))
    try:
        # as long as this doesn't throw an exception or return 4xx, we're ok
        subprocess.run(command.split(), check=True, stdout=subprocess.PIPE)
        log_results_simple(
            "ok",
            "ok",
            "positive",
            "account_whoami",
            "account whoami called successfully",
        )
        logger.info("account_whoami | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "account_whoami", "failed to call account whoami"
        )
        logger.error("account_whoami | error calling khulnasoft-cli: {0}".format(e))


# /Account commands

# Analysis archive
def analysis_archive(context):
    """Invoke the analysis_archive CLI subcommands."""
    logger.info("analysis-archive| starting subcommands")
    analysis_archive_images(context)
    analysis_archive_rules()


def analysis_archive_images(context):
    analysis_archive_images_add(context)
    analysis_archive_images_del(context)
    analysis_archive_images_get()
    analysis_archive_images_list()
    analysis_archive_images_restore()


def analysis_archive_images_add(context, test_type="positive"):
    """Invoke the analysis-archive images add CLI subcommand."""
    logger.info("analysis_archive_images_add | starting")

    try:
        image_data = random_image_data(context)
        image = "{0}:{1}".format(
            image_data[0]["image_detail"][0]["repo"],
            image_data[0]["image_detail"][0]["tag"],
        )
        image_sha = image_data[0]["image_detail"][0]["digest"]
    except Exception as e:
        logger.info(
            "analysis_archive_images_add | call failed; returning. Exception: {0}".format(
                e
            )
        )
        log_explicit_failure(
            test_type, "analysis_archive_images_add", "error {0}".format(e)
        )
        return

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug(
            "analysis_archive_images_add | running command {0}".format(wait_command)
        )
        logger.info(
            "analysis_archive_images_add | waiting for image {0} to be available".format(
                image
            )
        )
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "analysis_archive_images_add | something went a bit wrong waiting for image: {0}".format(
                e
            )
        )
        logger.info(
            "analysis_archive_images_add | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return
    try:
        command = assemble_command(
            context, " analysis-archive images add {0}".format(image_sha)
        )
        logger.debug(
            "analysis_archive_images_add | running command {0}".format(command)
        )
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("analysis_archive_images_add", response)
        status = response[0]["status"]
        log_results_simple(
            "archived",
            status,
            test_type,
            "analysis_archive_images_add",
            "archived image {0}".format(image),
        )
    except Exception as e:
        logger.debug(
            "analysis_archive_images_add | something went a bit wrong: {0}".format(e)
        )
        logger.info(
            "analysis_archive_images_add | call failed; returning. Exception: {0}".format(
                e
            )
        )
    logger.info("analysis_archive_images_add | finished")


def analysis_archive_images_del(context, test_type="positive"):
    """Invoke the analysis-archive images del CLI subcommand."""
    logger.info("analysis_archive_images_del | starting")

    try:
        image_data = random_image_data(context)
        image = "{0}:{1}".format(
            image_data[0]["image_detail"][0]["repo"],
            image_data[0]["image_detail"][0]["tag"],
        )
        image_sha = image_data[0]["image_detail"][0]["digest"]
    except Exception as e:
        logger.info(
            "analysis_archive_images_del | call failed; returning. Exception: {0}".format(
                e
            )
        )
        log_explicit_failure(
            test_type, "analysis_archive_images_del", "error {0}".format(e)
        )
        return

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug(
            "analysis_archive_images_del | running command {0}".format(wait_command)
        )
        logger.info(
            "analysis_archive_images_del | waiting for image {0} to be available".format(
                image
            )
        )
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "analysis_archive_images_del | something went a bit wrong waiting for image: {0}".format(
                e
            )
        )
        logger.info(
            "analysis_archive_images_del | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return
    try:
        command = assemble_command(
            context, " analysis-archive images del {0}".format(image_sha)
        )
        logger.debug(
            "analysis_archive_images_del | running command {0}".format(command)
        )
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("analysis_archive_images_del", response)
        # If the image was in the archive, the response will be empty; if not, it'll return
        # 404 w/a message in JSON, and a non-zero exit code from the CLI, which has to be
        # handled in the except clause below.
        # TODO Consider whether that (image not in archive) qualifies as a negative test
        if not response:
            log_results_simple(
                "ok",
                "ok",
                test_type,
                "analysis_archive_images_del",
                "deleted image {0} from archive".format(image),
            )
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            response = json.loads(e.stdout)
            status_code = response.get("httpcode")
            message = response.get("message")
            log_msg = "Attempted to delete image {0} from archive, but it was not in the archive; message: {1} HTTP status code: {2}"
            log_results_simple(
                "ok",
                "ok",
                test_type,
                "analysis_archive_images_del",
                log_msg.format(image, status_code, message),
            )
        else:
            logger.debug(
                "analysis_archive_images_del | something went a bit wrong: {0}".format(
                    e
                )
            )
            logger.info(
                "analysis_archive_images_del | call failed; returning. Exception: {0}".format(
                    e
                )
            )
    logger.info("analysis_archive_images_del | finished")


def analysis_archive_images_get():
    pass


def analysis_archive_images_list():
    pass


def analysis_archive_images_restore():
    pass


def analysis_archive_rules():
    analysis_archive_rules_add()
    analysis_archive_rules_del()
    analysis_archive_rules_get()
    analysis_archive_rules_list()


def analysis_archive_rules_add():
    pass


def analysis_archive_rules_del():
    pass


def analysis_archive_rules_get():
    pass


def analysis_archive_rules_list():
    pass


# /Analysis archive

# Evaluate
def evaluate(context):
    """Invoke the evaluate CLI subcommands."""
    logger.info("evaluate | starting subcommands")
    evaluate_check(context)


def evaluate_check(context, test_type="positive"):
    """Invoke the evaluate check CLI subcommand."""
    logger.info("evaluate_check | starting")

    image = random.choice(config.test_images)

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug("evaluate_check | running command {0}".format(wait_command))
        logger.info(
            "evaluate_check | waiting for image {0} to be available".format(image)
        )
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "evaluate_check | something went a bit wrong waiting for image: {0}".format(
                e
            )
        )
        logger.info(
            "evaluate_check | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return

    try:
        command = assemble_command(context, " evaluate check {0}".format(image))
        logger.debug("evaluate_check | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        if not response:
            log_explicit_failure(
                test_type,
                "evaluate_check",
                "could not evaluate image {0}".format(image),
            )
            return
        dump_response("evaluate_check", response)
        log_results_simple(
            "ok", "ok", test_type, "evaluate_check", "evaluated image {0}".format(image)
        )
    except Exception as e:
        logger.debug("evaluate_check | something went a bit wrong: {0}".format(e))
        logger.info("evaluate_check | call failed; returning. Exception: {0}".format(e))
    logger.info("evaluate_check | finished")


# /Evaluate

# Event
def event(context):
    """Invoke the event CLI subcommands."""
    logger.info("event | starting subcommands [fake]")
    event_delete()
    event_get()
    event_list()


def event_delete():
    pass


def event_get():
    pass


def event_list():
    pass


# /Event

# Image
def image(context):
    """Invoke the image CLI subcommands, other than image deletion (because other commands depend on images being in place)."""
    logger.info("image | starting subcommands")
    image_add(context)
    image_wait(context)
    image_get(context)
    image_content(context)
    image_content(context, content_type="malware")
    image_metadata(context)
    image_list(context)
    image_vuln(context)
    # image_import(context)


def image_deletion(context):
    """Invoke the image del CLI subcommand."""
    image_del(context, test_type="negative")
    image_del(context, force=True)


def image_add(context, test_type="positive"):
    """Invoke the image add CLI subcommand."""
    logger.info("image_add | starting")
    for image in config.test_images + config.malware_images + config.clean_images:
        command = assemble_command(context, " image add {0}".format(image))
        try:
            logger.debug("image_add | running command {0}".format(command))
            completed_proc = subprocess.run(
                command.split(), check=True, stdout=subprocess.PIPE
            )
            response = json.loads(completed_proc.stdout)
            image_status = response[0]["image_status"]
            logger.info(
                "image_add | added image {0}; status: {1}".format(image, image_status)
            )
            log_results_simple(
                image_status,
                "active",
                test_type,
                "image_add",
                "added image {0}".format(image),
            )
        except Exception as e:
            log_explicit_failure(
                test_type, "image_add", "failed to add image {0}".format(image)
            )
            logger.error("image_add | error calling khulnasoft-cli: {0}".format(e))
    logger.info("image_add | finished")


def image_content(context, test_type="positive", content_type="all"):
    """Invoke the image content CLI subcommand."""
    logger.info("image_content | starting")

    if content_type == "malware":
        image = random.choice(config.malware_images)
    else:
        image = random.choice(config.test_images)

    # Wait for the image to be available
    command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug("image_content | running command {0}".format(command))
        logger.info(
            "image_content | waiting for image {0} to be available".format(image)
        )
        subprocess.run(command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "image_content | something went a bit wrong waiting for image: {0}".format(
                e
            )
        )
        logger.info(
            "image_content | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return

    # Get the content types for our random image
    try:

        command = assemble_command(context, " image content {0}".format(image))
        logger.debug("image_content | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        if not response:
            log_explicit_failure(
                test_type,
                "image_content",
                "no content types for image {0}".format(image),
            )
            return

        logger.info(
            "image_content | found these content types for image {0}: {1}".format(
                image, response
            )
        )

        for content in response:
            # skip over other types if a content type is specified
            logger.info("image_content | content: {0}".format(content))
            if content_type != "all":
                if content != content_type:
                    continue
            command = assemble_command(
                context, " image content {0} {1}".format(image, content)
            )
            logger.debug("image_content | running command {0}".format(command))
            completed_proc = subprocess.run(
                command.split(), check=True, stdout=subprocess.PIPE
            )
            response = json.loads(completed_proc.stdout)
            content_length = len(response.get("content"))
            logger.info(
                "image_content | found {0} of content type {1} in image {2}".format(
                    content_length, content, image
                )
            )

    except Exception as e:
        logger.debug("image_content | something went a bit wrong: {0}".format(e))
        logger.info("image_content | call failed; returning. Exception: {0}".format(e))
        return

    log_results_simple(
        "ok",
        "ok",
        test_type,
        "image_content",
        "{0} content type(s) tested successfully".format(content_type),
    )
    logger.info("image_content | finished")


def image_del(context, force=False, test_type="positive"):
    """Invoke the image del CLI subcommand."""
    logger.info("image_del | starting")

    image = random.choice(config.test_images)
    command = assemble_command(context, " image del {0}".format(image))
    if force:
        command = assemble_command(context, " image del --force {0}".format(image))

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug("image_del | running command {0}".format(wait_command))
        logger.info("image_del | waiting for image {0} to be available".format(image))
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "image_del | something went a bit wrong waiting for image: {0}".format(e)
        )
        logger.info(
            "image_del | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return

    try:
        logger.debug("image_del | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        status = response.get("status")
        log_results_simple(
            "deleting", status, test_type, "image_del", "delete image {0}".format(image)
        )
        logger.info("image_del | finished")
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            response = json.loads(e.stdout)
            if (
                response.get("message")
                == "cannot delete image that is the latest of its tags, and has active subscription"
            ):
                if force:
                    log_explicit_failure(
                        test_type,
                        "image_del",
                        "could not delete image: {0}".format(image),
                    )
                else:
                    # assumes negative test... might not be a good idea
                    log_results_simple(
                        "ok",
                        "notok",
                        test_type,
                        "image_del",
                        "could not delete image without forcing: {0} (good)".format(
                            image
                        ),
                    )
        else:
            log_explicit_failure(test_type, "image_del", "failed to delete image")
            logger.error("image_del | error calling khulnasoft-cli: {0}".format(e))


def random_image_data(context):
    """Helper method to grab random image metadata (for one image)."""
    images = image_get(context, return_images=True, log=False)
    return random.choice(images)


# Note, you don't have to wait for the image to be available to call `image get`
def image_get(context, test_type="positive", return_images=False, log=True):
    """Invoke the image get CLI subcommand."""
    images = []
    if log:
        logger.info("image_get | starting")
    for image in config.test_images:
        command = assemble_command(context, " image get {0}".format(image))
        try:
            if log:
                logger.debug("image_get | running command {0}".format(command))
            completed_proc = subprocess.run(
                command.split(), check=True, stdout=subprocess.PIPE
            )
            if return_images:
                images.append(json.loads(completed_proc.stdout))
            # as long as this doesn't throw an exception or return 4xx, we're ok
            if log:
                log_results_simple(
                    "ok", "ok", test_type, "image_get", "got image {0}".format(image)
                )
        except Exception as e:
            log_explicit_failure(
                test_type, "image_get", "failed to get image {0}".format(image)
            )
            logger.error("image_get | error calling khulnasoft-cli: {0}".format(e))
    if return_images:
        if log:
            logger.info("image_get | finished")
        return images
    if log:
        logger.info("image_get | finished")


def image_import(context):
    pass


def image_list(context, test_type="positive"):
    """Invoke the image list CLI subcommand."""
    logger.info("image_list | starting")
    command = assemble_command(context, " image list")

    try:
        logger.debug("image_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_images = len(response)
        # as long as this doesn't throw an exception or return 4xx, we're ok
        log_results_simple(
            "ok",
            "ok",
            test_type,
            "image_list",
            "{0} images found".format(number_images),
        )
        logger.info("image_list | finished")
    except Exception as e:
        log_explicit_failure(test_type, "image_list", "failed to list images")
        logger.error("image_list | error calling khulnasoft-cli: {0}".format(e))


def image_metadata(context, test_type="positive"):
    """Invoke the image metadata CLI subcommand."""
    logger.info("image_metadata | starting")

    image = random.choice(config.test_images)
    command = assemble_command(context, " image metadata {0}".format(image))

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug("image_metadata | running command {0}".format(wait_command))
        logger.info(
            "image_metadata | waiting for image {0} to be available".format(image)
        )
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "image_metadata | something went a bit wrong waiting for image: {0}".format(
                e
            )
        )
        logger.info(
            "image_metadata | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return

    # First, we invoke the command without a metadata type; we expect to get back
    # a JSON blob w/manifest, docker_history, and dockerfile metadata types.
    # Then, we call for each of those types of metadata from the image.
    try:
        logger.debug("image_metadata | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        failed = False
        for key in config.metadata_types:
            if not key in response:
                failed = True
                log_explicit_failure(
                    test_type,
                    "image_metadata",
                    "{0} metadata type was not found for {1}".format(key, image),
                )
            subcommand = assemble_command(
                context, " image metadata {0} {1}".format(image, key)
            )
            sub_proc = subprocess.run(
                subcommand.split(), check=True, stdout=subprocess.PIPE
            )
            sub_json = json.loads(sub_proc.stdout)
            m_type = sub_json["metadata_type"]
            if not m_type or m_type != key:
                failed = True
                log_explicit_failure(
                    test_type,
                    "image_metadata",
                    "{0} was not expected metadata type {1} for image {2}".format(
                        m_type, key, image
                    ),
                )
        if not failed:
            log_results_simple(
                "ok",
                "ok",
                test_type,
                "image_metadata",
                "all expected metadata keys found",
            )
        logger.info("image_metadata | finished")
    except Exception as e:
        log_explicit_failure(
            test_type,
            "image_metadata",
            "failed to get image metadata for {0}".format(image),
        )
        logger.error("image_metadata | error calling khulnasoft-cli: {0}".format(e))


def image_vuln(context, test_type="positive"):
    """Invoke the image vuln CLI subcommand."""
    logger.info("image_vuln | starting")

    image = random.choice(config.test_images)

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug("image_vuln | running command {0}".format(wait_command))
        logger.info("image_vuln | waiting for image {0} to be available".format(image))
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "image_vuln | something went a bit wrong waiting for image: {0}".format(e)
        )
        logger.info(
            "image_vuln | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return

    try:
        failed = False
        for key in config.vulnerability_types:
            command = assemble_command(
                context, " image vuln {0} {1}".format(image, key)
            )
            logger.debug("image_vuln | running command: {0}".format(command))
            completed_proc = subprocess.run(
                command.split(), check=True, stdout=subprocess.PIPE
            )
            response = json.loads(completed_proc.stdout)
            vuln_type = response.get("vulnerability_type")
            num_vulns = len(response.get("vulnerabilities"))
            if not vuln_type or vuln_type != key:
                failed = True
                log_explicit_failure(
                    test_type,
                    "image_vuln",
                    "{0} was not expected vuln type {1} for image {2}".format(
                        vuln_type, key, image
                    ),
                )
            else:
                log_results_simple(
                    "ok",
                    "ok",
                    test_type,
                    "image_vuln",
                    "found {0} vuln of type {1} for image {2}".format(
                        num_vulns, key, image
                    ),
                )
        if not failed:
            log_results_simple(
                "ok", "ok", test_type, "image_vuln", "all expected metadata keys found"
            )
        logger.info("image_vuln | finished")
    except Exception as e:
        log_explicit_failure(
            test_type,
            "image_vuln",
            "failed to get vuln data for image {0}".format(image),
        )
        logger.error("image_vuln | error calling khulnasoft-cli: {0}".format(e))


def image_wait(context, timeout=-1, interval=5, test_type="positive"):
    logger.info("image_wait | starting")
    image = random.choice(config.test_images)
    command = assemble_command(
        context,
        " image wait {0} --timeout {1} --interval {2}".format(image, timeout, interval),
    )

    # Wait for the image to be available
    wait_command = assemble_command(context, " image wait {0}".format(image))
    try:
        logger.debug("image_wait | running command {0}".format(wait_command))
        logger.info("image_wait | waiting for image {0} to be available".format(image))
        subprocess.run(wait_command.split(), check=True, stdout=subprocess.PIPE)
    except Exception as e:
        logger.debug(
            "image_wait | something went a bit wrong waiting for image: {0}".format(e)
        )
        logger.info(
            "image_wait | call failed waiting for image; returning. Exception: {0}".format(
                e
            )
        )
        return

    try:
        logger.debug("image_wait | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        status = response[0]["analysis_status"]
        log_results_simple(
            "analyzed",
            status,
            test_type,
            "image_wait",
            "waited for image {0}".format(image),
        )
        logger.info("image_wait | finished")
    except Exception as e:
        logger.debug("image_wait | something went a bit wrong: {0}".format(e))
        logger.info("image_wait | call failed; returning. Exception: {0}".format(e))


# /Image

# Policy
def policy(context):
    """Invoke the policy CLI subcommands."""
    logger.info("policy | starting subcommands [fake]")
    policy_activate()
    policy_add()
    policy_del()
    policy_describe()
    policy_get()
    policy_hub()
    policy_list()


def policy_activate():
    pass


def policy_add():
    pass


def policy_del():
    pass


def policy_describe():
    pass


def policy_get():
    pass


def policy_hub():
    policy_hub_get()
    policy_hub_install()
    policy_hub_list()


def policy_hub_get():
    pass


def policy_hub_install():
    pass


def policy_hub_list():
    pass


def policy_list():
    """Invoke the policy CLI subcommands."""
    logger.info("policy_activate | starting")


# /Policy

# Query
def query(context):
    """Invoke the query CLI command."""
    logger.info("query | starting subcommands [fake]")


# /Query

# Repo
def repo(context):
    """Invoke the repo CLI subcommands."""
    logger.info("repo | starting subcommands")
    repo_add(context)
    repo_list(context)
    repo_get(context)
    repo_unwatch(context)
    repo_watch(context)
    repo_del(context)


def repo_add(context, test_type="positive"):
    """Invoke the repo add CLI subcommand."""
    logger.info("repo_add | starting")
    for repo in config.repositories:
        command = assemble_command(context, " repo add {0}".format(repo))
        try:
            logger.debug("repo_add | running command {0}".format(command))
            completed_proc = subprocess.run(
                command.split(), check=True, stdout=subprocess.PIPE
            )
            response = json.loads(completed_proc.stdout)
            dump_response("repo_add", response)
            repo_active = response[0]["active"]
            logger.info(
                "repo_add | added repo {0}; active: {1}".format(repo, repo_active)
            )
            # Repo might already exist and be unwatched; as long as there's no error we're ok
            log_results_simple(
                "ok", "ok", test_type, "repo_add", "added repo {0}".format(repo)
            )
        except Exception as e:
            log_explicit_failure(
                test_type, "repo_add", "failed to add repo {0}".format(repo)
            )
            logger.error("repo_add | error calling khulnasoft-cli: {0}".format(e))
    logger.info("repo_add | finished")


def repo_del(context, test_type="positive"):
    """Invoke the repo del CLI subcommand."""
    logger.info("repo_del | starting")

    repo = random.choice(config.repositories)
    command = assemble_command(context, " repo del {0}".format(repo))
    try:
        logger.debug("repo_del | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        # This is a bit silly, but the API/CLI is returning a byte literal w/newline, like: b'true\n'
        response = bool(strtobool(completed_proc.stdout.decode("utf-8").rstrip()))
        dump_response("repo_del", response)
        logger.info(
            "repo_del | repo {0} was deleted, and the response was {1}".format(
                repo, response
            )
        )
        log_results_simple(
            True, response, test_type, "repo_del", "repo {0} deleted".format(repo)
        )
        logger.info("repo_del | finished")
    except Exception as e:
        log_explicit_failure(test_type, "repo_del", "failed to del repo")
        logger.error("repo_del | error calling khulnasoft-cli: {0}".format(e))


def repo_get(context, test_type="positive"):
    """Invoke the repo get CLI subcommand."""
    logger.info("repo_get | starting")

    for repo in config.repositories:
        command = assemble_command(context, " repo get {0}".format(repo))
        try:
            logger.debug("repo_get | running command: {0}".format(command))
            completed_proc = subprocess.run(
                command.split(), check=True, stdout=subprocess.PIPE
            )
            response = json.loads(completed_proc.stdout)
            dump_response("repo_get", response)
            repo_active = response[0]["active"]
            # As long as this doesn't throw an exception or return 4xx, we're ok;
            # the repo might or might not be active/watched
            log_results_simple(
                "ok",
                "ok",
                test_type,
                "repo_get",
                "repo {0} status: {1}".format(repo, repo_active),
            )
            logger.info("repo_get | finished")
        except Exception as e:
            log_explicit_failure(
                test_type, "repo_get", "failed to get repo {0}".format(repo)
            )
            logger.error("repo_get | error calling khulnasoft-cli: {0}".format(e))
    logger.info("repo_get | finished")


def repo_list(context, test_type="positive"):
    """Invoke the repo list CLI subcommand."""
    logger.info("repo_list | starting")

    command = assemble_command(context, " repo list")
    try:
        logger.debug("repo_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("repo_list", response)
        number_repos = len(response)
        # as long as this doesn't throw an exception or return 4xx, we're ok
        log_results_simple(
            "ok", "ok", test_type, "repo_list", "{0} repos found".format(number_repos)
        )
        logger.info("repo_list | finished")
    except Exception as e:
        log_explicit_failure(test_type, "repo_list", "failed to list repos")
        logger.error("repo_list | error calling khulnasoft-cli: {0}".format(e))


def repo_unwatch(context, test_type="positive"):
    """Invoke the repo unwatch CLI subcommand."""
    logger.info("repo_unwatch | starting")

    repo = random.choice(config.repositories)
    command = assemble_command(context, " repo unwatch {0}".format(repo))
    try:
        logger.debug("repo_unwatch | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("repo_unwatch", response)
        repo_active = response[0]["active"]
        logger.info(
            "repo_unwatch | repo {0} was unwatched, and active status is {1}".format(
                repo, repo_active
            )
        )
        log_results_simple(
            False,
            repo_active,
            test_type,
            "repo_unwatch",
            "repo {0} unwatched".format(repo),
        )
        logger.info("repo_unwatch | finished")
    except Exception as e:
        log_explicit_failure(test_type, "repo_unwatch", "failed to unwatch repo")
        logger.error("repo_unwatch | error calling khulnasoft-cli: {0}".format(e))


def repo_watch(context, test_type="positive"):
    """Invoke the repo watch CLI subcommand."""
    logger.info("repo_watch | starting")

    repo = random.choice(config.repositories)
    command = assemble_command(context, " repo watch {0}".format(repo))
    try:
        logger.debug("repo_watch | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("repo_watch", response)
        repo_active = response[0]["active"]
        logger.info(
            "repo_watch | repo {0} was watched, and active status is {1}".format(
                repo, repo_active
            )
        )
        log_results_simple(
            True, repo_active, test_type, "repo_watch", "repo {0} watched".format(repo)
        )
        logger.info("repo_watch | finished")
    except Exception as e:
        log_explicit_failure(test_type, "repo_watch", "failed to watch repo")
        logger.error("repo_watch | error calling khulnasoft-cli: {0}".format(e))


# /Repo

# Subscription
def subscription(context):
    """Invoke the subscription CLI subcommands."""
    logger.info("subscription | starting subcommands")
    subscription_list(context)
    subscription_activate(context)
    subscription_deactivate(context)


def subscription_get_one(context):
    """Helper method to grab just one subscription."""
    command = assemble_command(context, " subscription list")
    try:
        logger.debug("subscription_get_one | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        sub = random.choice(response)
        logger.debug("subscrption_get_one | returning subscription {0}".format(sub))
        return sub
    except Exception as e:
        logger.error("subscription_get_one | error calling khulnasoft-cli: {0}".format(e))


def subscription_list(context, test_type="positive"):
    """Invoke the subscription list CLI subcommand."""
    logger.info("subscription_list | starting")

    command = assemble_command(context, " subscription list")
    try:
        logger.debug("subscription_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        number_subs = len(response)
        logger.info("subscrption_list | found {0} subscriptions".format(number_subs))
        dump_response("subscription_list", response)
        for sub in response:
            logger.debug("subscription_list | {0}".format(sub))
        log_results_simple(
            "ok",
            "ok",
            test_type,
            "subscription_list",
            "{0} subscriptions found".format(number_subs),
        )
        logger.info("subscription_list | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "subscription_list", "failed to list subscriptions"
        )
        logger.error("subscription_list | error calling khulnasoft-cli: {0}".format(e))


def subscription_activate(context, test_type="positive"):
    """Invoke the subscription activate CLI subcommand."""
    logger.info("subscription_activate | starting")

    sub = subscription_get_one(context)
    logger.info("subscription_activate | got {0}".format(sub))
    sub_key = sub["subscription_key"]
    sub_type = sub["subscription_type"]
    command = assemble_command(
        context, " subscription activate {0} {1}".format(sub_type, sub_key)
    )
    try:
        logger.debug("subscription_activate | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("subscription_activate", response)
        sub_active = response[0]["active"]
        logger.info(
            "subscrption_activate | subscription active: {0}".format(sub_active)
        )
        log_results_simple(
            True,
            sub_active,
            test_type,
            "subscription_activate",
            "subscription {0}/{1} should be active".format(sub_type, sub_key),
        )
        logger.info("subscription_activate | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "subscription_activate", "failed to activate subscription"
        )
        logger.error("subscription_activate | error calling khulnasoft-cli: {0}".format(e))


def subscription_deactivate(context, test_type="positive"):
    """Invoke the subscription deactivate CLI subcommand."""
    logger.info("subscription_deactivate | starting")

    sub = subscription_get_one(context)
    logger.info("subscription_deactivate | got {0}".format(sub))
    sub_key = sub["subscription_key"]
    sub_type = sub["subscription_type"]
    command = assemble_command(
        context, " subscription deactivate {0} {1}".format(sub_type, sub_key)
    )
    try:
        logger.debug("subscription_deactivate | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("subscription_deactivate", response)
        sub_active = response[0]["active"]
        logger.info(
            "subscrption_deactivate | subscription active: {0}".format(sub_active)
        )
        log_results_simple(
            False,
            sub_active,
            test_type,
            "subscription_deactivate",
            "subscription {0}/{1} should not be active".format(sub_type, sub_key),
        )
        logger.info("subscription_deactivate | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "subscription_deactivate", "failed to deactivate subscription"
        )
        logger.error(
            "subscription_deactivate | error calling khulnasoft-cli: {0}".format(e)
        )


# /Subscription

# System
def system(context):
    """Invoke the system CLI subcommands."""
    logger.info("system | starting subcommands")
    system_status(context)
    system_errorcodes(context)
    system_del()


def system_del():
    pass


def system_feeds(context):
    system_feeds_list(context)
    system_feeds_config(context)
    system_feeds_delete(context)
    # system_feeds_sync(context)


def system_feeds_sync():
    pass


def system_feeds_config(context):
    system_feeds_config_toggle(context, enable=False)
    system_feeds_config_toggle(context, enable=True)
    system_feeds_config_toggle(context, enable=False)
    system_feeds_config_toggle(context, enable=True)
    # leave a group disabled so it can be deleted
    system_feeds_config_toggle(context, enable=False)


def system_feeds_config_toggle(context, test_type="positive", enable=True):
    """Invoke the system feeds config enable or disable CLI subcommand.
    If the enable parameter is True, the command 'system feeds config enable'
    is invoked. If the enable parameter is False, the command
    'system feeds config disable' is invoked. This function is ideally
    called first with enable=False, then again with enable=True; otherwise,
    there might not be a disabled feed to enable, which shows up as a test
    failure."""

    action = "enabling" if enable else "disabling"
    looking_for = "disabled" if enable else "enabled"
    end_state = "enabled" if enable else "disabled"
    toggle_flag = "--enable" if enable else "--disable"

    logger.info(
        "system_feeds_config_toggle | starting | {0}, looking for {1}".format(
            action, looking_for
        )
    )

    # Iterate through the feeds, then groups, until e find a (en|dis)abled group
    # to toggle. Doing this randomly instead leads to rather more code, so even if
    # this is naive (as it just takes the first thing it can toggle) it's simpler.
    feeds = system_feeds_list(context, return_feeds=True, log=False)
    if not feeds:
        logger.info("system_feeds_config_toggle | No feeds available")
        log_explicit_failure(
            test_type, "system_feeds_config_toggle", "No feeds available"
        )
        return

    for feed in feeds:
        for group in feed["groups"]:
            if group["enabled"] != enable:
                break

    # Did we find one? It should != the param enable.
    if group["enabled"] == enable:
        message = "failed to find a {0} group in any feed".format(looking_for)
        logger.info("system_feeds_config_toggle | " + message)
        log_explicit_failure(test_type, "system_feeds_config_toggle", message)
        return

    # Ok, we're clear. Carry on.
    feed_name = feed["name"]
    group_name = group["name"]
    command = assemble_command(
        context,
        " system feeds config --group {0} {1} {2}".format(
            group_name, toggle_flag, feed_name
        ),
    )
    try:
        logger.debug(
            "system_feeds_config_toggle | running command: {0}".format(command)
        )
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("system_feeds_config_toggle", response[0])
        if response[0]["enabled"] == enable:
            message = "{0} feed {1} group {2}".format(end_state, feed_name, group_name)
            log_results_simple(
                "ok", "ok", test_type, "system_feeds_config_toggle", message
            )
        else:
            message = "failed {0} feed {1} group {2}".format(
                action, feed_name, group_name
            )
            log_explicit_failure(test_type, "system_feeds_config_toggle", message)
            return
        logger.info("system_feeds_config_toggle | finished")
    except Exception as e:
        log_explicit_failure(
            test_type,
            "system_feeds_config_toggle",
            "failed {0} feed/group".format(action),
        )
        logger.error(
            "system_feeds_config_toggle | error calling khulnasoft-cli: {0}".format(e)
        )


def system_feeds_delete(context, test_type="positive"):
    """Invoke the system feeds delete CLI subcommand."""
    logger.info("system_feeds_delete | starting")

    # Get feeds/groups, find one that's disabled, delete it
    feeds = system_feeds_list(context, return_feeds=True, log=False)
    if not feeds:
        logger.info("system_feeds_delete | No feeds available")
        log_explicit_failure(test_type, "system_feeds_delete", "No feeds available")
        return

    for feed in feeds:
        for group in feed["groups"]:
            if group["enabled"] == False:
                break

    feed_name = feed["name"]
    group_name = group["name"]
    command = assemble_command(
        context, " system feeds delete --group {0} {1}".format(group_name, feed_name)
    )
    try:
        logger.debug("system_feeds_delete | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("system_feeds_config_toggle", response[0])
        # Enabled shows up as false after deletion, but I don't see a status otherwise;
        # other than getting an error from the API, I assume this worked
        if response[0]["enabled"] == False:
            message = "Deleted feed {0} group {1}".format(feed_name, group_name)
            log_results_simple("ok", "ok", test_type, "system_feeds_delete", message)
        else:
            message = "Failed deleting feed {0} group {1}".format(feed_name, group_name)
            log_explicit_failure(test_type, "system_feeds_delete", message)
            return
        logger.info("system_feeds_delete | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "system_feeds_delete", "failed {0} feed/group".format(action)
        )
        logger.error("system_feeds_delete | error calling khulnasoft-cli: {0}".format(e))


def system_feeds_list(context, test_type="positive", return_feeds=False, log=True):
    """Invoke the system feeds list CLI subcommand."""
    if log:
        logger.info("system_feeds_list | starting")

    command = assemble_command(context, " system feeds list")
    try:
        if log:
            logger.debug("system_feeds_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        if log:
            dump_response("system_feeds_list", response[0])
            for feed in response:
                logger.debug("feed: {0}".format(feed["name"]))
                for group in feed["groups"]:
                    logger.debug(
                        "    group: {0}; records: {1}".format(
                            group["name"], group["record_count"]
                        )
                    )
        number_feeds = len(response)
        # as long as this doesn't throw an exception or return 4xx, we're ok
        if log:
            log_results_simple(
                "ok",
                "ok",
                test_type,
                "system_feeds_list",
                "{0} feeds found".format(number_feeds),
            )
            logger.info("system_feeds_list | finished")
        if return_feeds:
            return response
    except Exception as e:
        if log:
            log_explicit_failure(test_type, "system_feeds_list", "failed to list feeds")
            logger.error("system_feeds_list | error calling khulnasoft-cli: {0}".format(e))
        return


def system_status(context, test_type="positive"):
    """Invoke the system status CLI subcommand."""
    logger.info("system_status | starting")

    command = assemble_command(context, " system status")
    try:
        logger.debug("system_status | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("system_status", response)
        for service in response.get("service_states"):
            if type(service["service_detail"]) == str:
                service_detail = service["service_detail"]
            else:
                service_detail = service["service_detail"]["up"]
            logger.info(
                "system_status | service: {0}; up: {1}".format(
                    service["servicename"], service_detail
                )
            )
        number_services = len(response.get("service_states"))
        log_results_simple(
            "ok",
            "ok",
            test_type,
            "system_status",
            "{0} services found".format(number_services),
        )
        logger.info("system_status | finished")
    except Exception as e:
        log_explicit_failure(test_type, "system_status", "failed to get system status")
        logger.error("system_status | error calling khulnasoft-cli: {0}".format(e))


def system_errorcodes(context, test_type="positive"):
    """Invoke the system errorcodes CLI subcommand."""
    logger.info("system_errorcodes | starting")

    command = assemble_command(context, " system errorcodes")
    try:
        logger.debug("system_errorcodes | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("system_errorcodes", response)
        for code in response:
            logger.info("system_errorcodes | error code: {0}".format(code["name"]))
        number_errorcodes = len(response)
        log_results_simple(
            "ok",
            "ok",
            test_type,
            "system_errorcodes",
            "{0} error codes found".format(number_errorcodes),
        )
        logger.info("system_errorcodes | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "system_errorcodes", "failed to get system error codes"
        )
        logger.error("system_errorcodes | error calling khulnasoft-cli: {0}".format(e))


def system_wait(context, log=True):
    if log:
        logger.info("system_wait | starting")
    image = random.choice(config.test_images)
    wait = config.default_system_wait_timeout
    interval = config.default_system_wait_interval

    command = assemble_command(
        context, " system wait --timeout {0} --interval {1}".format(wait, interval)
    )
    try:
        if log:
            logger.debug("system_wait | running command {0}".format(command))
            logger.info(
                "system_wait | waiting for system to be available".format(image)
            )
        subprocess.run(command.split(), check=True, stdout=subprocess.PIPE)
        if log:
            log_results_simple(
                "ok", "ok", "positive", "system_wait", "waited for system"
            )
            logger.info("image_wait | finished")
    except Exception as e:
        if log:
            logger.debug("system_wait | something went a bit wrong: {0}".format(e))
            logger.info(
                "system_wait | call failed; returning. Exception: {0}".format(e)
            )
        return


# /System

# Registry
def registry(context):
    """Invoke the registry CLI subcommands."""
    logger.info("registry | starting subcommands")
    load_dotenv()
    if (
        not os.getenv("REGISTRY_URL")
        or not os.getenv("REGISTRY_USER")
        or not os.getenv("REGISTRY_TOKEN")
    ):
        logger.info(
            "registry | No registry URL or credentials; skipping registry commands."
        )
        return

    registry_add(context)
    registry_add(context)
    registry_list(context)
    registry_get(context)
    registry_update(context)
    registry_del(context)


def registry_add(context):
    """Invoke the registry add CLI subcommand."""
    logger.info("registry_add | starting")
    reg = os.getenv("REGISTRY_URL")
    reg_user = os.getenv("REGISTRY_USER")
    reg_token = os.getenv("REGISTRY_TOKEN")
    command = assemble_command(
        context, " registry add {0} {1} {2}".format(reg, reg_user, reg_token)
    )
    try:
        logger.debug("registry_add | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        reg_name = response[0]["registry_name"]
        reg_type = response[0]["registry_type"]
        reg_user = response[0]["registry_user"]
        logger.info(
            "registry_add | added reg {0} {1} {2}".format(reg_name, reg_type, reg_user)
        )
        log_results_simple(
            "ok",
            "ok",
            "positive",
            "registry_add",
            "added registry {0}".format(reg_name),
        )
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            response = json.loads(e.stdout)
            if response.get("message") == "registry already exists in DB":
                log_results_simple(
                    "ok",
                    "notok",
                    "negative",
                    "registry_add",
                    "registry {0} already exists".format(reg),
                )
            else:
                log_explicit_failure(
                    test_type, "registry_add", "failed to add registry {0}".format(reg)
                )
                logger.error("registry_add | error calling khulnasoft-cli: {0}".format(e))
    logger.info("registry_add | finished")


def registry_get(context, test_type="positive"):
    """Invoke the registry get CLI subcommand."""
    logger.info("registry_get | starting")
    reg = random.choice(config.registries)
    command = assemble_command(context, " registry get {0}".format(reg))
    try:
        logger.debug("registry_get | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        reg_name = response[0]["registry_name"]
        reg_type = response[0]["registry_type"]
        reg_user = response[0]["registry_user"]
        logger.info(
            "registry_get | got reg {0} {1} {2}".format(reg_name, reg_type, reg_user)
        )
        log_results_simple(
            "ok", "ok", "positive", "registry_get", "got registry {0}".format(reg_name)
        )
    except Exception as e:
        log_explicit_failure(
            test_type, "registry_get", "failed to get registry {0}".format(reg)
        )
        logger.error("registry_get | error calling khulnasoft-cli: {0}".format(e))
    logger.info("registry_get | finished")


def registry_list(context, test_type="positive"):
    """Invoke the registry list CLI subcommand."""
    logger.info("resgisrty_list | starting")

    command = assemble_command(context, " registry list")
    try:
        logger.debug("registry_list | running command: {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        response = json.loads(completed_proc.stdout)
        dump_response("registry_list", response)
        num_reg = len(response)
        for reg in response:
            logger.info(
                "registry_list | registry {0}, type {1}, user {2}".format(
                    reg["registry"], reg["registry_type"], reg["registry_user"]
                )
            )
        log_results_simple(
            "ok",
            "ok",
            "positive",
            "registry_list",
            "Found {0} registries".format(num_reg),
        )
        logger.info("registry_list | finished")
    except Exception as e:
        log_explicit_failure(test_type, "registry_list", "failed to list registries")
        logger.error("registry_list | error calling khulnasoft-cli: {0}".format(e))


def registry_update(context):
    pass


def registry_del(context, test_type="positive"):
    """Invoke the registry del CLI subcommand."""
    logger.info("registry_del | starting")
    reg = os.getenv("REGISTRY_URL")
    command = assemble_command(context, " registry del {0}".format(reg))
    try:
        logger.debug("registry_del | running command {0}".format(command))
        completed_proc = subprocess.run(
            command.split(), check=True, stdout=subprocess.PIPE
        )
        # Like with repo_del: the API/CLI is returning a byte literal w/newline, like: b'true\n'
        response = bool(strtobool(completed_proc.stdout.decode("utf-8").rstrip()))
        dump_response("registry_del", response)
        logger.info(
            "registry_del | registry {0} was deleted, and the response was {1}".format(
                reg, response
            )
        )
        log_results_simple(
            True,
            response,
            test_type,
            "registry_del",
            "registry {0} deleted".format(reg),
        )
        logger.info("registry_del | finished")
    except Exception as e:
        log_explicit_failure(
            test_type, "registry_del", "failed to del registry {0}".format(reg)
        )
        logger.error("registry_del | error calling khulnasoft-cli: {0}".format(e))


# /Registry

logger = make_logger()
positive_tests = {"pass": [], "fail": []}
negative_tests = {"pass": [], "fail": []}
root_context = dict()

cmd_prefix = config.cmd_prefix
api_url = config.local_url
if os.path.isfile("CLI"):
    api_url = config.ci_url
    cmd_prefix = config.cli_command_prefix + config.cmd_prefix


def run_cli_driver():

    root_context["user"] = config.default_admin_user
    root_context["password"] = config.default_admin_pass
    root_context["api_url"] = api_url
    context = copy.deepcopy(root_context)

    # Wait for the system to be up and ready before doing anything else
    logger.info("main | Waiting for system to be ready")
    system_wait(context, False)

    # Figure out which top level CLI command is being called, then call it
    command = sys.argv[1] if len(sys.argv) == 2 else "all"
    if command == "all":
        account(context)
        context = copy.deepcopy(root_context)
        image(context)
        analysis_archive(context)
        image_deletion(context)
        evaluate(context)
        repo(context)
        event(context)
        policy(context)
        subscription(context)
        # Note that system feeds subcommands are not tested here since they can
        # take a long time; run system_feeds() explicitly for that
        system(context)
        registry(context)
    else:
        func = getattr(sys.modules[__name__], command)
        func(context)

    log_results_summary()


if __name__ == "__main__":
    run_cli_driver()
