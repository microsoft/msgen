# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Main argument parsing functionality"""
import argparse
import re
import sys
from collections import namedtuple

import malibuargsactions

PACKAGE_NAME = "msgen"
PROGRAM_NAME = "msgen"

def print_generic_help():
    """Prints generic help for the program"""
    description = """A command-line tool to run genomics processes on the Microsoft Genomics
platform. To learn more about each command, please run "msgen help <command>".
See also https://pypi.python.org/pypi/msgen"""
    common_arguments = _common_help + """
Here is an example of how you can do that:

api_url_base : https://<domain.name>
access_key   : <access key>

Note that values provided in the command line override values provided in the
configuration file."""
    print "usage:" + _usage
    print
    print description
    print
    print common_arguments

def parse(argv, submit_func, list_func, cancel_func, status_func, help_func):
    """Parse provided arguments and return the result"""
    parser = _get_parser(submit_func, list_func, cancel_func, status_func, help_func)
    return malibuargsactions.validate_namespace(parser, parser.parse_args(argv))

def parse_and_run(argv, submit_func, list_func, cancel_func, status_func, help_func):
    """Parse all arguments and run a command associated with the specified subparser"""
    # Print help, if no arguments provided
    if len(sys.argv) == 1:
        print_generic_help()
        sys.exit(1)
    args = parse(sys.argv[1:], submit_func, list_func, cancel_func, status_func, help_func)
    args.run_command(args)

class ArgsOutput(object):
    """Class that contains all arguments passed to app"""
    def __init__(self):
        """Constructor"""

        # This is where we keep all defaults. Let's not set them up in the parser so that we don't
        # have inconsistencies
        self.access_key = ""
        self.command = ""
        self.workflow_id = ""
        self.process_name = "snapgatk"
        self.process_args = ""
        self.description = ""

        self.input_storage_account_type = "AZURE_BLOCK_BLOB"
        self.input_storage_account_name = ""
        self.input_storage_account_key = ""
        self.input_storage_account_container = ""
        self.input_blob_name_1 = []
        self.input_blob_name_2 = []

        self.output_storage_account_type = "AZURE_BLOCK_BLOB"
        self.output_storage_account_name = ""
        self.output_storage_account_key = ""
        self.output_storage_account_container = ""
        self.output_overwrite = False
        self.output_filename_base = ""
        self.output_include_logfiles = True
        self.sas_duration = 48

        self.api_url_base = ""
        self.poll = False
        self.workflow_class = ""

        self.bqsr_enabled = None
        self.read_group = None
        self.ignore_azure_region = None
        self.emit_ref_confidence = None
        self.bgzip_output = None

        self.input_dictionary = dict()
        self.output_dictionary = dict()

        # list filtering arguments
        self.in_range = None
        self.outcome = None
        self.with_description = None
        self.with_process = None
        self.export_to = None
        self.output_file = None

    def __set_args_value(self, key, value):
        """Sets class properties from key value pair"""
        if value is None:
            # Do not override defaults
            return
        if key == "command":
            setattr(self, key, str(value).upper())
            return
        setattr(self, key, value)

    def fill(self, args):
        """Fills the object properties with the parsed argument values."""
        for key, value in vars(args).iteritems():
            self.__set_args_value(key, value)

    def get_storage_accounts_info(self):
        """
        Returns a named tuple with the input and output storage information
        """
        AccountInfo = namedtuple(
            "AccountInfo",
            "name key container")
        StorageInfo = namedtuple(
            "StorageInfo",
            "input output")
        storage_info = StorageInfo(
            AccountInfo(
                self.input_storage_account_name,
                self.input_storage_account_key,
                self.input_storage_account_container),
            AccountInfo(
                self.output_storage_account_name,
                self.output_storage_account_key,
                self.output_storage_account_container))

        return storage_info

# Include range notation into allowed negative values (so that it's not parsed as an unknown option).
# Will match these:
#  * -5
#  * -.5
#  * -5.5
#  * -5:
#  * -5:5
#  * -5:-5
_negative_number_matcher = re.compile(r"^-\d+:?$|^-\d*\.\d+$|^-\d+:-?\d+$")


_action_commands = ["submit", "list", "cancel", "status"]
_usage = "\n    {0} help [{1}]\n".format(PROGRAM_NAME, "|".join(c for c in _action_commands)) + \
    "\n".join("    {0} {1} ...".format(PROGRAM_NAME, c) for c in _action_commands)

_common_help = """All commands require two arguments to interact with the Microsoft Genomics
service: -u/--api-url-base and -k/--access-key. The former is the base URI for
the API, and the latter is one of your access keys which you can find on the
'Access keys' blade of you Genomics account in Azure portal. These values can
also be part of the config file that you can provide using the -f/--config-file
option. """

def _get_parser(submit_func, list_func, cancel_func, status_func, help_func):
    """Returns a parser that reads arguments for all commands and calls
    a function provided for each command once its arguments are parsed"""

    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False, prog=PROGRAM_NAME)
    common_required = common_parser.add_argument_group("common required arguments")
    common_required.add_argument("-u", "--api-url-base",
                                 metavar="URL",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="Microsoft Genomics API URL")
    common_required.add_argument("-k", "--access-key",
                                 metavar="KEY",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="your Microsoft Genomics access key")
    common_optional = common_parser.add_argument_group("common optional arguments")
    common_optional.add_argument("-f", "--config-file",
                                 metavar="CONFIG",
                                 action=malibuargsactions.ConfigFileReader,
                                 help="""settings file to look for command-line arguments; command-line arguments will take precedence and override
                                 file contents""")

    parser = argparse.ArgumentParser(add_help=False, prog=PROGRAM_NAME, usage=_usage)

    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    # LIST
    list_parser = subparsers.add_parser("list", parents=[common_parser], add_help=False,
                                        description=_common_help + """The rest of the options give you a way to filter and export results.
                                        Note that filtering is applied before the range (-r/--in-range).""", prog=PROGRAM_NAME+" list")
    list_optional = list_parser.add_argument_group("optional arguments for listing workflows")
    list_optional.add_argument("-r", "--in-range",
                               metavar="N|N:M",
                               required=False,
                               action=malibuargsactions.RangeValidator,
                               help="""index or Python-like range for filtering workflows with some restrictions; 0 is the oldest workflow,
                               -1 is the most recent, and either N or M is optional""")
    list_optional.add_argument("-o", "--outcome",
                               metavar="fail|pass",
                               required=False,
                               choices=["fail", "pass"],
                               type=str.lower,
                               help="include only workflows that have finished with a given outcome")
    list_optional.add_argument("-d", "--with-description",
                               metavar="SUBSTRING",
                               required=False,
                               help="include only workflows with a given substring in their description")
    list_optional.add_argument("-p", "--with-process",
                               metavar="SUBSTRING",
                               required=False,
                               help="include only workflows with a given substring in their process name")
    list_optional.add_argument("-e", "--export-to",
                               metavar="csv",
                               required=False,
                               choices=["csv"],
                               type=str.lower,
                               help="show results in CSV instead of as a list")
    list_optional.add_argument("-of", "--output-file",
                               metavar="FILE",
                               required=False,
                               help="store results in a file instead of printing them on the screen")
    list_parser.set_defaults(run_command=list_func)
    # Don't treat negative ranges as unknown options
    list_parser._negative_number_matcher = _negative_number_matcher

    # SUBMIT
    submit_parser = subparsers.add_parser("submit", parents=[common_parser], add_help=False,
                                          description=_common_help + """Submitting a workflow requires additional arguments to let the service know
                                          where input files are located, where to place the output, and so on.""", prog=PROGRAM_NAME+" submit")
    submit_required = submit_parser.add_argument_group("required arguments for submitting a workflow")
    submit_required.add_argument("-pa", "--process-args",
                                 metavar="ARGS",
                                 required=True,
                                 type=malibuargsactions.process_args_validator,
                                 help="""arguments for the genomics process; this is usually used to specify a desired reference genome, for example,
                                 'R=b37m1' or 'R=hg19m1' or 'R=hg38m1' or 'R=hg38m1x'""")
    submit_required.add_argument("-ia", "--input-storage-account-name",
                                 metavar="ACCOUNT",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="Azure storage account name where input files reside")
    submit_required.add_argument("-ik", "--input-storage-account-key",
                                 metavar="KEY",
                                 required=False,
                                 help="Azure storage account key which will be used to create temporary access tokens for input files")
    submit_required.add_argument("-ic", "--input-storage-account-container",
                                 metavar="CONTAINER",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="Azure blob container where input files reside")
    submit_required.add_argument("-b1", "--input-blob-name-1",
                                 metavar="BLOBNAME",
                                 required=True,
                                 type=malibuargsactions.input_validator,
                                 nargs="+",
                                 help="first file name; SAS token can be appended")
    submit_required.add_argument("-b2", "--input-blob-name-2",
                                 metavar="BLOBNAME",
                                 required=False,
                                 type=malibuargsactions.input_validator,
                                 nargs="+",
                                 help="second file name, needed only if input is in the FASTQ format; SAS token can be appended")
    submit_required.add_argument("-oa", "--output-storage-account-name",
                                 metavar="ACCOUNT",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="Azure storage account name where output files will be placed")
    submit_required.add_argument("-ok", "--output-storage-account-key",
                                 metavar="KEY",
                                 required=False,
                                 help="Azure storage account key which will be used to create a temporary access token for an output container")
    submit_required.add_argument("-oc", "--output-storage-account-container",
                                 metavar="CONTAINER",
                                 required=True,
                                 type=malibuargsactions.output_container_validator,
                                 help="Azure blob container where output files will be placed; SAS token can be appended")

    submit_optional = submit_parser.add_argument_group("optional arguments for submitting a workflow")
    submit_optional.add_argument("-p", "--process-name",
                                 metavar="PROCESS",
                                 required=False,
                                 type=malibuargsactions.nstr,
                                 help="name of the genomics process; by default, the latest is used, which is equivalent to 'snapgatk'")
    submit_optional.add_argument("-it", "--input-storage-account-type",
                                 metavar="AZURE_BLOCK_BLOB",
                                 required=False,
                                 help=argparse.SUPPRESS)
    submit_optional.add_argument("-ot", "--output-storage-account-type",
                                 metavar="AZURE_BLOCK_BLOB",
                                 required=False,
                                 help=argparse.SUPPRESS)
    submit_optional.add_argument("-d", "--description",
                                 metavar="TEXT",
                                 required=False,
                                 action=malibuargsactions.MaxLengthValidator, max_length=500,
                                 help="short workflow description")
    submit_optional.add_argument("-ow", "--output-overwrite",
                                 metavar="true|false",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help="if 'true', existing output files may be overwritten; default value is 'false'")
    submit_optional.add_argument("-of", "--output-filename-base",
                                 metavar="NAME",
                                 required=False,
                                 type=malibuargsactions.output_validator,
                                 help="base name to be used for all output files")
    submit_optional.add_argument("-ol", "--output-include-logfiles",
                                 metavar="true|false",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help="if 'true', log files will be uploaded to the output container along with results; default value is 'true'")
    submit_optional.add_argument("-sas", "--sas-duration",
                                 metavar="HOURS",
                                 required=False,
                                 action=malibuargsactions.PositiveIntValidator,
                                 help="access token duration for input blobs/output container, in hours")
    submit_optional.add_argument("-pl", "--poll",
                                 metavar="true|false",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help="if 'false', the client will return immediately, otherwise, will keep polling for the status after submission; default value is 'false'")
    submit_optional.add_argument("-bqsr", "--bqsr-enabled",
                                 metavar="true|false",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help="if 'false', will skip the BQSR step; default value is 'true'")
    submit_optional.add_argument("-rg", "--read-group",
                                 metavar="READ GROUP LINE",
                                 required=False,
                                 type=malibuargsactions.read_group_validator,
                                 help="an optional read group line that will override the default read group created by the process")
    submit_optional.add_argument("-wc", "--workflow-class",
                                 required=False,
                                 action=malibuargsactions.MaxLengthValidator, max_length=100,
                                 help=argparse.SUPPRESS)
    submit_optional.add_argument("-sf", "--suppress-fastq-validation",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help=argparse.SUPPRESS)
    submit_optional.add_argument("-ar", "--ignore-azure-region",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help=argparse.SUPPRESS)
    submit_optional.add_argument("-erc", "--emit-ref-confidence",
                                 choices=["none", "gvcf"],
                                 required=False,
                                 type=str.lower,
                                 help="value 'gvcf' supported; default value is 'none' which produces VCF output")
    submit_optional.add_argument("-bz", "--bgzip-output",
                                 metavar="true|false",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help="if 'true', will zip vcf/gvcf files using bgzip, and create an index using tabix; default value is 'false' for vcf output and 'true' for gvcf output")
    submit_parser.set_defaults(run_command=submit_func)

    # CANCEL
    cancel_parser = subparsers.add_parser("cancel", parents=[common_parser], add_help=False,
                                          description=_common_help + "Cancelling a workflow also requires a workflow ID.", prog=PROGRAM_NAME+" cancel")
    cancel_required = cancel_parser.add_argument_group("required arguments for canceling a workflow")
    cancel_required.add_argument("-w", "--workflow-id",
                                 metavar="ID",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="workflow ID returned after submission")
    cancel_optional = cancel_parser.add_argument_group("optional arguments for canceling a workflow")
    cancel_optional.add_argument("-pl", "--poll",
                                 metavar="true|false",
                                 required=False,
                                 type=malibuargsactions.to_bool,
                                 help="if 'false', the client will return immediately, otherwise, will keep polling for the status after cancellation; default value is 'false'")
    cancel_parser.set_defaults(run_command=cancel_func)

    # STATUS
    status_parser = subparsers.add_parser("status", parents=[common_parser], add_help=False,
                                          description=_common_help + "Getting a status of a workflow also requires a workflow ID.", prog=PROGRAM_NAME+" status")
    status_required = status_parser.add_argument_group("required arguments for canceling a workflow")
    status_required.add_argument("-w", "--workflow-id",
                                 metavar="ID",
                                 required=True,
                                 type=malibuargsactions.nstr,
                                 help="workflow ID returned after submission")
    status_parser.set_defaults(run_command=status_func)

    # HELP
    help_parser = subparsers.add_parser("help", add_help=False)
    help_parser.add_argument("cmd", nargs="?")
    help_parser.set_defaults(run_command=lambda a: help_func(a, subparsers))

    return parser
