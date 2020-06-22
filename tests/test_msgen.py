# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Unit tests for msgen.py"""
import sys
import unittest
from cStringIO import StringIO
from msgen_cli.msgen import warn_for_package_update

class TestMsgen(unittest.TestCase):
    """Unit tests for msgen.py"""
    def test_warn_for_package_update_message_says_newer(self):
        """Tests if warn_for_package_update says new version available"""
        result = False 
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        redirected_output = sys.stdout

        try:
            warn_for_package_update("0.7.0")
            result = True
        except Exception as exception:
            print str(exception)

        # restore stdout
        sys.stdout = old_stdout

        if not result:
            raise Exception("Failed")
        print_result = str(redirected_output.getvalue())
        message = "newer version of msgen is available"
        self.assertTrue(message in print_result)

    def test_warn_for_package_update_message_says_nothing(self):
        """Tests if warn_for_package_update is silent if latest"""
        result = False 
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        redirected_output = sys.stdout

        try:
            warn_for_package_update("10.0.0")
            result = True
        except Exception as exception:
            print str(exception)

        # restore stdout
        sys.stdout = old_stdout

        if not result:
            raise Exception("Failed")
        print_result = str(redirected_output.getvalue())
        self.assertTrue(print_result == "")


if __name__ == '__main__':
    unittest.main()
