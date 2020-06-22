# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""File for common functionality"""
import os
import random
import string
import sys
from calendar import timegm
from collections import namedtuple
from email.utils import formatdate
from time import sleep

EXIT_MESSAGE_VIEWTIME = 10

def pause_and_display(message, debug_mode=True):
    """Pause and show a message so it can be read by a human"""
    if debug_mode:
        for second in range(0, EXIT_MESSAGE_VIEWTIME):
            print message + str(EXIT_MESSAGE_VIEWTIME-second) + " second(s)."
            sleep(1)

def get_api_url_from_base(base_url):
    """Get the full URL given a base URL"""
    if base_url.endswith("/") != True:
        base_url += "/"
    base_url += "api/workflows/"
    return base_url

def get_current_path():
    """Get the current path of the running app"""
    return os.path.dirname(os.path.realpath(sys.argv[0]))

def randomword(length):
    """Gets a random string of the given length"""
    return ''.join(random.choice(string.lowercase) for i in range(length))

def format_rfc1123(datetime_object):
    """Formats a datetime object according to RFC 1123"""
    if datetime_object is None:
        return ""
    timestamp = timegm(datetime_object.utctimetuple())
    return formatdate(timestamp, usegmt=True)

ODataArguments = namedtuple("ODataArguments", "orderby skip top")
ORDER_ASC = "asc"
ORDER_DESC = "desc"
