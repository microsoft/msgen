# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Test argument parsing"""
import unittest
import msgen_cli.malibuargs as malibuargs

class TestParse(unittest.TestCase):
    def test_parse_runs_successfully_with_full_command_line_options(self):
        argv = "status -u https://url --access-key key -w 123".split()
        args = malibuargs.parse(argv, None, None, None, None, None)
        self.assertEquals(args.command, "status")
        self.assertEquals(args.api_url_base, "https://url")
        self.assertEquals(args.access_key, "key")
        self.assertEquals(args.workflow_id, "123")

    def test_parse_runs_successfully_with_options_from_config(self):
        argv = "status -f tests/unittestconfig.txt -w 123".split()
        args = malibuargs.parse(argv, None, None, None, None, None)
        self.assertEquals(args.command, "status")
        self.assertEquals(args.workflow_id, "123")

    def test_parse_fails_without_required_options(self):
        argv = "submit -u https://url --access-key key -b1 blob1".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_fails_without_inputs(self):
        argv = "submit -f tests/unittestconfig.txt".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv + ["-b1", "", "-b2", ""], None, None, None, None, None)

    def test_parse_fails_with_mixed_bam_fastq(self):
        argv = "submit -f tests/unittestconfig.txt".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv + ["-b1", "file1.bam"], None, None, None, None, None)

    def test_parse_fails_with_uneven_fastq(self):
        argv = "submit -f tests/unittestconfig.txt".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv + ["-b2", ""], None, None, None, None, None)

    def test_parse_fails_with_no_known_files(self):
        argv = "submit -f tests/unittestconfig.txt".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv + ["-b2", "file.txt", "-b1", "file.jpg"], None, None, None, None, None)

    def test_parse_runs_successfully_with_uneven_bam(self):
        argv = "submit -f tests/unittestconfig.txt".split()
        using_key = False
        with open("tests/unittestconfig.txt", 'r') as file:
            for line in file:
                if "input_storage_account_key" in line.lower():
                    using_key = True
                    break
        if using_key:
            args = malibuargs.parse(argv + ["-b2", "file1.bam", "-b1", "file1.sam", "file2.sam"], None, None, None, None, None)
            self.assertListEqual(args.input_blob_name_1, ["file1.sam", "file2.sam"])
            self.assertListEqual(args.input_blob_name_2, ["file1.bam"])
        else:
            args = malibuargs.parse(argv + ["-b2", "file1.bam?sas", "-b1", "file1.sam?sas", "file2.sam?sas"], None, None, None, None, None)
            self.assertListEqual(args.input_blob_name_1, ["file1.sam?sas", "file2.sam?sas"])
            self.assertListEqual(args.input_blob_name_2, ["file1.bam?sas"])

    def test_parse_runs_successfully_with_unmatching_fastq_names(self):
        argv = "submit -f tests/unittestconfig.txt".split()
        using_key = False
        with open("tests/unittestconfig.txt", 'r') as file:
            for line in file:
                if "input_storage_account_key" in line.lower():
                    using_key = True
                    break
        if using_key:
            args = malibuargs.parse(argv + ["-b2", "file1.fq"], None, None, None, None, None)
            blobs1 = args.input_blob_name_1
            blobs2 = args.input_blob_name_2
            blobs1_parsed = []
            blobs2_parsed = []
            for blob in blobs1:
                if "?" in blob:
                    blob = blob.split("?")[0]
                blobs1_parsed.append(blob)
            for blob in blobs2:
                if "?" in blob:
                    blob = blob.split("?")[0]
                blobs2_parsed.append(blob)
            self.assertListEqual(blobs1_parsed, ["chr21-10k_1.fq.gz"])
            self.assertListEqual(blobs2_parsed, ["file1.fq"])
        else:
            args = malibuargs.parse(argv + ["-b2", "file1.fq?sas"], None, None, None, None, None)
            blobs1 = args.input_blob_name_1
            blobs2 = args.input_blob_name_2
            blobs1_parsed = []
            blobs2_parsed = []
            for blob in blobs1:
                if "?" in blob:
                    blob = blob.split("?")[0]
                blobs1_parsed.append(blob)
            for blob in blobs2:
                if "?" in blob:
                    blob = blob.split("?")[0]
                blobs2_parsed.append(blob)
            self.assertListEqual(blobs1_parsed, ["chr21-10k_1.fq.gz"])
            self.assertListEqual(blobs2_parsed, ["file1.fq"])


    def test_parse_fails_when_command_missing(self):
        argv = "-f tests/unittestconfig.txt".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_fails_on_wrong_command(self):
        argv = "do -f tests/unittestconfig.txt".split()
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_handles_negative_range_value(self):
        argv = "list -u https://url -k key -r -5:-1".split()
        args = malibuargs.parse(argv, None, None, None, None, None)
        self.assertIsNotNone(args.in_range)

    def test_parse_skips_missing_config(self):
        argv = "list -u https://url -k key -f imaginary.config".split()
        args = malibuargs.parse(argv, None, None, None, None, None)
        self.assertEquals(args.command, "list")
        self.assertEquals(args.api_url_base, "https://url")
        self.assertEquals(args.access_key, "key")

    def test_parse_empty_bools_keeps_defaults(self):
        argv = "cancel -u https://url -k key -w 123".split()
        args = malibuargs.parse(argv + ["-pl", ""], None, None, None, None, None)
        args_output = malibuargs.ArgsOutput()
        args_output.fill(args)
        self.assertEquals(args_output.command, "CANCEL")
        self.assertEquals(args_output.api_url_base, "https://url")
        self.assertEquals(args_output.access_key, "key")
        self.assertEquals(args_output.workflow_id, "123")
        self.assertEquals(args_output.poll, False)

def create_valid_args_output_for_submission():
    return ["submit",
            "--api-url-base", "http://url",
            "--access-key", "key",
            "--input-storage-account-container", "icontainer",
            "--input-storage-account-key", "ikey",
            "--input-storage-account-name", "iaccount",
            "--output-storage-account-container", "ocontainer",
            "--output-storage-account-key", "okey",
            "--output-storage-account-name", "oaccount",
            "--input-blob-name-1", "i1.fq",
            "--input-blob-name-2", "i2.fq",
            "--process-args", "R=reference"]


class TestValidateSubmit(unittest.TestCase):
    def test_parse_submit_arguments_on_full_set(self):
        argv = create_valid_args_output_for_submission()
        result = malibuargs.parse(argv, None, None, None, None, None)
        self.assertIsNotNone(result)

    def test_parse_submit_fails_if_one_io_arg_missing(self):
        argv = create_valid_args_output_for_submission()
        missing = ["--process-args",
                   "--input-storage-account-container", "--input-storage-account-key", "--input-storage-account-name",
                   "--output-storage-account-container", "--output-storage-account-key", "--output-storage-account-name"]
        for arg in missing:
            i = argv.index(arg)
            argv[i+1] = ""
            with self.assertRaises(SystemExit):
                malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_submit_fails_if_both_input_blobs_missing(self):
        argv = create_valid_args_output_for_submission()
        i, j = argv.index("--input-blob-name-1"), argv.index("--input-blob-name-2")
        argv = argv[:i] + argv[j+2:]
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_submit_succeeds_if_second_input_blob_missing_for_bam(self):
        argv = create_valid_args_output_for_submission()
        i, j = argv.index("--input-blob-name-1"), argv.index("--input-blob-name-2")
        argv[i+1] = "i.bam"
        argv = argv[:j] + argv[j+2:]
        result = malibuargs.parse(argv, None, None, None, None, None)
        self.assertIsNotNone(result)

class TestNegativeMatcher(unittest.TestCase):

    def test_accepts_intended_values(self):
        self.assertIsNotNone(malibuargs._negative_number_matcher.match("-5"))
        self.assertIsNotNone(malibuargs._negative_number_matcher.match("-.5"))
        self.assertIsNotNone(malibuargs._negative_number_matcher.match("-5.5"))
        self.assertIsNotNone(malibuargs._negative_number_matcher.match("-5:"))
        self.assertIsNotNone(malibuargs._negative_number_matcher.match("-5:5"))
        self.assertIsNotNone(malibuargs._negative_number_matcher.match("-5:-5"))

    def test_rejects_unintended_values(self):
        self.assertIsNone(malibuargs._negative_number_matcher.match("-f"))
        self.assertIsNone(malibuargs._negative_number_matcher.match("-5."))
        self.assertIsNone(malibuargs._negative_number_matcher.match("-5.f"))
        self.assertIsNone(malibuargs._negative_number_matcher.match("-f:"))
        self.assertIsNone(malibuargs._negative_number_matcher.match("-5:f"))
        self.assertIsNone(malibuargs._negative_number_matcher.match("-5:-5f"))

class TestEmitRefConfidence(unittest.TestCase):
    def test_parse_submit_fails_if_erc_not_supported(self):
        argv = create_valid_args_output_for_submission()
        argv.extend(["--emit-ref-confidence", "vcf"])
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_submit_succeeds_if_erc_valid(self):
        argv = create_valid_args_output_for_submission()
        argv.extend(["--emit-ref-confidence", "gvcf"])
        result = malibuargs.parse(argv, None, None, None, None, None)
        self.assertIsNotNone(result)

class TestBgzipOutput(unittest.TestCase):
    def test_parse_submit_fails_if_bz_not_supported(self):
        argv = create_valid_args_output_for_submission()
        argv.extend(["--bgzip-output", "Invalid"])
        with self.assertRaises(SystemExit):
            malibuargs.parse(argv, None, None, None, None, None)

    def test_parse_submit_succeeds_if_bz_valid(self):
        argv = create_valid_args_output_for_submission()
        argv.extend(["--bgzip-output", "true"])
        result = malibuargs.parse(argv, None, None, None, None, None)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
