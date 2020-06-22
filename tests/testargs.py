# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Test arguments"""
import msgen_cli.malibuargs as malibuargs

def get_test_args():
    """Creates an instance of ArgsOutput for unit testing purposes  """
    args = malibuargs.parse("submit -f tests/unittestconfig.txt".split(), None, None, None, None, None)
    args_output = malibuargs.ArgsOutput()
    args_output.fill(args)
    return args_output
