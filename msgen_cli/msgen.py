#!/usr/bin/python
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Microsoft Genomics command-line client - allows submission and management
 of genomics workflows on the Microsoft Genomics platform"""

import sys
from datetime import datetime
import malibuworkflow
import malibuargs

# Version must be valid form for StrictVersion <d>.<d>.<d> for the sort
# to work properly and find the latest version.  More details at:
# http://epydoc.sourceforge.net/stdlib/distutils.version.StrictVersion-class.html
VERSION = '0.9.0'

def warn_for_package_update(current_version):
    """Check for updated version of msgen and warn if a newer version is available"""
    pypiRoot = "https://pypi.python.org"
    connect_timeout = 0.1
    read_timeout = 0.1
    url = pypiRoot

    try:
        import requests
        from distutils.version import StrictVersion

        # Construct the URL to get the msgen package information from pypi
        #   and extract pypi's version information from the payload
        url = "{0}/pypi/{1}/json".format(pypiRoot, malibuargs.PACKAGE_NAME)
        json = requests.get(url, timeout=(connect_timeout, read_timeout)).json()
        if "releases" not in json:
            raise ValueError()
        versions = json["releases"].keys()
        if len(versions) == 0:
            return
        versions.sort(key=StrictVersion, reverse=True)
        if current_version < versions[0]:
            print "\n*** INFO ***" \
                  "\nA newer version of msgen is available.  Please consider upgrading to v{0:s}." \
                  "\n    To upgrade, run: pip install --upgrade msgen" \
                  "\n".format(versions[0])
    except ValueError:
        print "\n*** INFO ***" \
              "\nInvalid JSON received by {0} when checking for updates." \
              "\n".format(url)
    except (requests.Timeout, requests.ConnectionError, requests.exceptions.RequestException):
        print "\n*** INFO ***" \
              "\nUnable to connect to {0} to check for updates." \
              "\n".format(pypiRoot)

def _command(func, args):
    """Perform a command using command-line arguments
    func: A method of the malibuworkflow.WorkflowExecutor class"""
    args_output = malibuargs.ArgsOutput()
    args_output.fill(args)
    workflow_executor = malibuworkflow.WorkflowExecutor(args_output)
    func(workflow_executor)
    sys.exit(workflow_executor.current_exit_status)

def post_workflow(args):
    """Post a workflow using command-line arguments"""
    _command(malibuworkflow.WorkflowExecutor.post_workflow, args)

def get_workflow_status(args):
    """Get status of a workflow using command-line arguments"""
    _command(malibuworkflow.WorkflowExecutor.get_workflow_status, args)

def cancel_workflow(args):
    """Cancel a workflow using command-line arguments"""
    _command(malibuworkflow.WorkflowExecutor.cancel_workflow, args)

def list_workflows(args):
    """List workflows using command-line arguments"""
    _command(malibuworkflow.WorkflowExecutor.list_workflows, args)

def print_help(args, subparsers):
    """Print general help or help for a specific command"""
    if args.cmd is None or args.cmd == "help":
        malibuargs.print_generic_help()
    else:
        subparser = subparsers.choices.get(args.cmd, None)
        if subparser is None:
            malibuargs.print_generic_help()
        else:
            subparser.print_help()

def main():
    """Main execution flow"""

    # Display logon banner
    print "Microsoft Genomics command-line client v{0}".format(VERSION)
    print "Copyright (c) {0} Microsoft. All rights reserved.".format(datetime.utcnow().year)

    warn_for_package_update(VERSION)

    malibuargs.parse_and_run(sys.argv, post_workflow, list_workflows, cancel_workflow, get_workflow_status, print_help)

if __name__ == "__main__":
    main()
