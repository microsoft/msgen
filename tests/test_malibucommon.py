# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Test common functions"""
import unittest
from datetime import datetime
import msgen_cli.malibucommon as malibucommon

class TestMalibuCommon(unittest.TestCase):

    def test_format_rfc1123_formats(self):
        date = datetime(year=2017, month=1, day=17, hour=23, minute=57, second=31,) 
        result = malibucommon.format_rfc1123(date)

        self.assertEquals("Tue, 17 Jan 2017 23:57:31 GMT", result)

    def test_format_rfc1123_accepts_None(self):
        result = malibucommon.format_rfc1123(None)
        self.assertEquals("", result)

if __name__ == '__main__':
    unittest.main()
