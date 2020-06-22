# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Test arguments"""
import msgen_cli.malibuargs as malibuargs

def get_test_args():
    """Creates an instance of ArgsOutput for unit testing purposes  """
    args = malibuargs.parse("submit -f tests/unittestconfig.txt".split(), None, None, None, None, None)
    args_output = malibuargs.ArgsOutput()
    args_output.fill(args)
    return args_output
