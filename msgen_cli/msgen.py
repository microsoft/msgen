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
VERSION = '0.9.1'

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

    malibuargs.parse_and_run(sys.argv, post_workflow, list_workflows, cancel_workflow, get_workflow_status, print_help)

if __name__ == "__main__":
    main()
