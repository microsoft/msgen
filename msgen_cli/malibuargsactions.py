# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Custom argument parsing actions"""
import argparse
import itertools
import os
import re
import string
import sys
from malibucommon import ODataArguments, ORDER_ASC, ORDER_DESC

class MaxLengthValidator(argparse.Action):
    """String length validator"""
    def __init__(self, option_strings, max_length, *args, **kwargs):
        super(MaxLengthValidator, self).__init__(option_strings, *args, **kwargs)
        self.max_length = max_length

    def __call__(self, parser, namespace, values, option_string=None):
        if values is not None and len(values) > self.max_length:
            print "Maximum length for the '{0}' field is {1}. Your value will be truncated.".format(self.dest, self.max_length)
            values = values[:self.max_length]
        setattr(namespace, self.dest, values)

class PositiveIntValidator(argparse.Action):
    """Positive integer validator"""
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            positive = int(values)
        except ValueError as e:
            raise argparse.ArgumentError(self, e.message)
        if positive <= 0:
            raise argparse.ArgumentError(self, "expected a positive value")
        setattr(namespace, self.dest, positive)

class RangeValidator(argparse.Action):
    """Range validator for listing workflows"""
    def __call__(self, parser, namespace, values, option_string=None):
        value = values.strip()

        if not value or value == ":":
            raise argparse.ArgumentError(self, "an index or a range is expected")

        if ":" not in value:
            single = int(value)
            if single < 0:
                setattr(namespace, self.dest, ODataArguments(orderby=ORDER_DESC, skip=abs(single)-1, top=1))
            else:
                setattr(namespace, self.dest, ODataArguments(orderby=ORDER_ASC, skip=single, top=1))
            return

        start, stop = [s.strip() for s in value.split(":", 1)]

        try:
            start = int(start) if start else None
            stop = int(stop) if stop else None
        except ValueError as e:
            raise argparse.ArgumentError(self, e.message)

        # start and stop cannot both be None here, this would raise a parser error above
        if start is None and stop < 0:
            setattr(namespace, self.dest, ODataArguments(orderby=ORDER_DESC, skip=abs(stop), top=None))
            return
        elif start is None and stop >= 0:
            setattr(namespace, self.dest, ODataArguments(orderby=ORDER_ASC, skip=None, top=stop))
            return
        elif start < 0 and stop is None:
            setattr(namespace, self.dest, ODataArguments(orderby=ORDER_DESC, skip=None, top=abs(start)))
            return
        elif start >= 0 and stop is None:
            setattr(namespace, self.dest, ODataArguments(orderby=ORDER_ASC, skip=start, top=None))
            return
        elif start >= 0 and stop >= 0:
            # OK to have negative $top, our controller returns [] in that case, like in Python
            setattr(namespace, self.dest, ODataArguments(orderby=ORDER_ASC, skip=start, top=max(0, stop-start)))
            return
        elif start < 0 and stop < 0:
            # OK to have negative $top, our controller returns [] in that case, like in Python
            setattr(namespace, self.dest, ODataArguments(orderby=ORDER_DESC, skip=abs(stop), top=max(0, abs(start)-abs(stop))))
            return
        else:
            raise argparse.ArgumentError(self, "when a range is specified, its ends should be both non-negative or both negative")

class ConfigFileReader(argparse.Action):
    """Configuration file reader"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        if not values or not os.path.isfile(values):
            print >> sys.stderr, "Path '{0}' is not a file or doesn't exist, not reading settings from it".format(values)
        else:
            expected_settings, expected_list_settings = self.__get_expected_config_setting_names(parser)
            with open(values) as f:
                options_list = self.__read_options_from_file(f, expected_settings, expected_list_settings)
                for option in options_list:
                    action = parser._option_string_actions.get(option, None)
                    # Ignore arguments from other subparsers
                    if not action:
                        pass
                    # Prevent specifying a config file from the config we are reading
                    if action == self:
                        pass
                    # Check if we have seen this setting yet in the command line, and act on it, if not
                    if getattr(namespace, action.dest) is None:
                        raw_value = options_list[option]
                        # Convert the raw value to the target type; need to handle lists explicitly
                        if isinstance(raw_value, list):
                            converted_value = [parser._get_value(action, v) for v in raw_value]
                        else:
                            converted_value = parser._get_values(action, [raw_value])
                        action(parser, namespace, converted_value, option)
                        # The following is a hack: since ArgumentParser checks for whether values were provided
                        # by keeping a registry (inaccessible to us) istead of checking the namespace,
                        # mark the action as not required
                        action.required = False

    def __get_expected_config_setting_names(self, parser):
        """Returns a list of settings that we can expect to find in a config file"""
        all_options = self.__collect_settings_by_filter(parser)
        list_options = self.__collect_settings_by_filter(parser, lambda a: a.nargs is not None)
        return all_options, list_options

    def __collect_settings_by_filter(self, parser, condition=lambda a: True):
        options = set()
        options.update(itertools.chain.from_iterable(a.option_strings for a in parser._actions if condition(a)))
        return set(option[2:] for option in filter(lambda o: o.startswith("--"), options))

    def __read_options_from_file(self, file_object, expected_settings, expected_list_settings):
        """Reads expected settings from the provided config file
        file_object: File object for the config file
        expected_settings: settings we expect to find in the config"""
        if not file_object:
            raise Exception("file cannot be None")
        options = {}
        for line in file_object:
            line = line.strip() if line else ""
            if not line or line.startswith("#"):
                continue
            columns = line.split(':', 1)
            if len(columns) == 2:
                key = columns[0].strip().replace("_", "-")
                if key in expected_list_settings:
                    # We can do this because whitespace is not allowed
                    options["--" + key] = columns[1].strip().split()
                elif key in expected_settings:
                    value = columns[1].strip()
                    if value:
                        options["--" + key] = value
        return options

def nstr(value):
    """String converter that checks for contents"""
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("a non-empty, non-whitespace string is expected")
    return value

def to_bool(value):
    """String converter that checks for contents"""
    value = value.strip().lower()
    error = "a 'true' or 'false' is expected"
    if not value:
        # Keep default values when parsing empty strings from config
        return None
    elif value == "true":
        return True
    elif value == "false":
        return False
    raise argparse.ArgumentTypeError(error)

BAD_BLOB_CHARS = re.compile("[^A-Za-z0-9._/-]")
BAD_SAS_CHARS = re.compile("[^A-Za-z0-9&?=%/-]")
def _blob_name_validator(value, is_input = False):
    """Blob name validator based on regular expression"""
    # Name length 1-1024 (https://docs.microsoft.com/en-us/azure/guidance/guidance-naming-conventions#naming-rules-and-restrictions)
    # Characters: alphanumeric, dot, dash, slash, and underscore.  

    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("empty or whitespace-only names are not allowed; found [{}]".format(value))
    if len(value) > 1024:
        raise argparse.ArgumentTypeError("maximum length is 1024 characters; found a value of length {0}".format(len(value)))
    if value.startswith("/"):
        raise argparse.ArgumentTypeError("blob names cannot start with a slash; found [{0}]".format(value))
    
    blob_name_parts = value.split("?")   
    blob_name_parts_count = len(blob_name_parts)

    if bool(BAD_BLOB_CHARS.search(blob_name_parts[0])):
        error = "each name should only contain alphanumeric characters, dot, hyphen, underscore, and slash"
        raise argparse.ArgumentTypeError(error + "; found [{0}]".format(blob_name_parts[0]))
    if is_input:
        if blob_name_parts_count == 2:
            if bool(BAD_SAS_CHARS.search(blob_name_parts[1])):
                error = "each SAS token should only contain alphanumeric characters, question mark, equals, percent, slash, hyphen and ampersand"
                raise argparse.ArgumentTypeError(error + "; found [{0}]".format(blob_name_parts[1]))
        elif blob_name_parts_count > 2:
            raise argparse.ArgumentTypeError("blob names cannot have more than one question market; found a value of length {0}".format(blob_name_parts_count)) 
    else:
        if blob_name_parts_count > 1:
            raise argparse.ArgumentTypeError("output SAS token can only be appended to the container name")

    return value


def _output_container_name_validator(value):
    """Blob name validator based on regular expression"""   
    container_name_parts = value.split("?")   
    container_name_parts_count = len(container_name_parts)

    if bool(BAD_BLOB_CHARS.search(container_name_parts[0])):
        error = "container name should only contain alphanumeric characters and hyphens"
        raise argparse.ArgumentTypeError(error + "; found [{0}]".format(container_name_parts[0]))
    if container_name_parts_count == 2:
        if bool(BAD_SAS_CHARS.search(container_name_parts[1])):
            error = "each SAS token should only contain alphanumeric characters, question mark, equals, percent, slash, hyphen and ampersand"
            raise argparse.ArgumentTypeError(error + "; found [{0}]".format(container_name_parts[1]))
    elif container_name_parts_count > 2:
        raise argparse.ArgumentTypeError("container names cannot have more than one question market; found a value of length {0}".format(container_name_parts_count)) 

    return value

BAD_REFERENCE_CHARS = re.compile("[^A-Za-z0-9]")
ARG_DELIMITER = ";"
KEY_VALUE_DELIMITER = "="
def _process_args_validator(value):
    """Process args validator \\"""
    if not value or value is None:
        raise argparse.ArgumentTypeError("a non-empty, non-whitespace string is expected")
    value = value.strip()
    if not value or value is None:
        raise argparse.ArgumentTypeError("a non-empty, non-whitespace string is expected")
    kv_pairs = value.split(ARG_DELIMITER)
    for kv_pair in kv_pairs:
        kv = kv_pair.split(KEY_VALUE_DELIMITER)
        if kv[0]=="R":
            if bool(BAD_REFERENCE_CHARS.search(kv[1])):
                error = "the reference should only contain alphanumeric characters"
                raise argparse.ArgumentTypeError(error + "; found [{0}]".format(value))
    return value

def process_args_validator(value):
    """Process arguments validator"""
    return _process_args_validator(value)

def input_validator(value):
    """Input blob name validator"""
    return _blob_name_validator(value, True)

def output_validator(value):
    """Output blob name validator"""
    if not value or not value.strip():
        return None
    return _blob_name_validator(value.strip(), False)

def output_container_validator(value):
    """Output container name validator"""
    return _output_container_name_validator(value)

ALLOWED_READ_GROUP_CHARACTERS = set(string.letters + string.digits + string.punctuation + " \t") - set("=;")
MAX_READ_GROUP_LENGTH = 1000

def read_group_validator(value):
    """Read group line validator"""
    if not value or not value.strip():
        return None
    value = value.strip()
    if len(value) > MAX_READ_GROUP_LENGTH:
        raise argparse.ArgumentTypeError("read group line should not exceed 1000 characters; found {0}".format(len(value)))
    if not value.startswith("@RG"):
        raise argparse.ArgumentTypeError("read group line should start with @RG; found [{0}]".format(value))
    illegal = filter(lambda c: c not in ALLOWED_READ_GROUP_CHARACTERS, value)
    if len(illegal) > 0:
        raise argparse.ArgumentTypeError("read group line may contain only ASCII letters and numbers, some punctuation, and spaces; found illegal characters [{0}]".format(illegal))
    return value.replace("\t", "\\t")

BAM_SAM_FILE = re.compile(r"^.+\.(b|s)am$", re.IGNORECASE)
FASTQ_FILE = re.compile(r"^.+\.f(ast)?q(\.gz)?$", re.IGNORECASE)

def differ_in_at_most_one(first, second):
    """Check if two strings differ in at most one position."""
    # Check if length differences make it possible
    if abs(len(first) - len(second)) > 1:
        return False

    if len(first) > len(second):
        longer, shorter = first, second
    else:
        longer, shorter = second, first

    one_found = False
    l, s = 0, 0
    long_length = len(longer)
    short_length = len(shorter)
    while l < long_length and s < short_length:
        if longer[l] != shorter[s]:
            if one_found: # found second difference
                return False
            else:
                one_found = True
                # skip one, if we have different lengths
                # position in shorter string should stay in place in that case
                if long_length != short_length:
                    l += 1
                else:
                    l += 1
                    s += 1
        else:
            l += 1
            s += 1
    return True

_name_mismatch_error = """File names [{0}] and [{1}] differ in more than one character.
This may mean that reads in them are not paired which will cause an error during alignment.
If you are sure that these two files contain paired reads, you can suppress this message by provding an argument -sf/--suppress-fastq-validation with a value 'true'"""

def validate_namespace(parser, namespace):
    """Do additional checks on the whole set of parsed arguments. Only those checks that cannot be performed
    in single argument validators (e.g. dependency between arguments apart from mutual exclusion) should be
    done here."""
    if namespace.command != "submit":
        return namespace

    if (namespace.output_storage_account_key and 
        namespace.output_storage_account_container and 
        "?" in namespace.output_storage_account_container):
        raise parser.error("cannot specify an output storage account key AND a SAS token.  You must only use a key, or only use a SAS token")

    if (not namespace.output_storage_account_key and
        (not namespace.output_storage_account_container or
        "?" not in namespace.output_storage_account_container)):
        raise parser.error("you must include either an output storage account key or output storage account container SAS token")

    # 0. Make sure we have something as input.
    if not namespace.input_blob_name_1:
        namespace.input_blob_name_1 = []
    if not namespace.input_blob_name_2:
        namespace.input_blob_name_2 = []

    all_blob_names = []
    key_provided_for_blob = False
    if namespace.input_storage_account_key:
        key_provided_for_blob = True

    for blob_name in namespace.input_blob_name_1 + namespace.input_blob_name_2:
        if "?" in blob_name:
            if namespace.input_storage_account_key:
                raise parser.error("cannot specify an input storage account key AND blob SAS tokens.  You must only use a key, or only use SAS tokens")
            blob_name_parts = blob_name.split("?")
            all_blob_names.append(blob_name_parts[0])
        else:
            if not key_provided_for_blob:
                # no key and NO SAS token
                raise parser.error("you must include either an input storage account key or blob SAS token(s)")
            all_blob_names.append(blob_name)

    if len(all_blob_names) == 0:
        raise parser.error("no inputs provided")

    if (namespace.emit_ref_confidence == "gvcf") and namespace.bgzip_output is False:
        print "Warning: \"g.vcf\" output will not be compressed by bgzip because argument '-bz' or '--bgzip-output' was set to false"

    # 1. Make sure we don't mix BAM/SAM and FASTQ files in a single submission.
    bam_sam = any(BAM_SAM_FILE.match(b) != None for b in all_blob_names)
    fastq = any(FASTQ_FILE.match(b) != None for b in all_blob_names)
    if bam_sam and fastq:
        raise parser.error("cannot mix both FASTQ and BAM/SAM files in inputs")
    elif not (bam_sam or fastq):
        raise parser.error("neither FASTQ nor BAM/SAM files were provided as inputs")
    elif fastq:
        # 2. Make sure that if we use FASTQ files, we have them in pairs
        if len(namespace.input_blob_name_1) != len(namespace.input_blob_name_2):
            raise parser.error("each FASTQ file provided in -b1/--input-blob-name-1 should be paired with a FASTQ file in -b2/--input-blob-name-2 at the same position")
        # 3. If names in each pair don't match, show a warning
        for first, second in zip(namespace.input_blob_name_1, namespace.input_blob_name_2):
            if "?" in first:
                first = first.split("?")[0]
            if "?" in second:
                second = second.split("?")[0]
            if first == second:
                raise parser.error("the same file is used at the same position in both -b1/--input-blob-name-1 and -b2/--input-blob-name-2: [{0}]".format(first))
            if not differ_in_at_most_one(first, second) and not namespace.suppress_fastq_validation:
                print >> sys.stderr, _name_mismatch_error.format(first, second)
    
    return namespace
