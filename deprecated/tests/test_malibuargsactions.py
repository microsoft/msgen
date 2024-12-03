# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Test custom argument actions"""
import unittest
import argparse
import testargs
import msgen_cli.malibuargsactions as malibuargsactions

class TestArgLengthValidator(unittest.TestCase):

    def test_truncates_long_value(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.MaxLengthValidator, max_length=3)
        result = parser.parse_args(["--argument", "1234"])
        self.assertEquals(result.argument, "123")

    def test_does_not_modify_short_value(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.MaxLengthValidator, max_length=5)
        result = parser.parse_args(["--argument", "1234"])
        self.assertEquals(result.argument, "1234")

    def test_accepts_none(self):
        parser = argparse.ArgumentParser(self)
        parser.add_argument("--argument", action=malibuargsactions.MaxLengthValidator, max_length=5)
        result = parser.parse_args(["--argument", None])
        self.assertEquals(result.argument, None)

    def test_truncates_to_zero(self):
        parser = argparse.ArgumentParser(self)
        parser.add_argument("--argument", action=malibuargsactions.MaxLengthValidator, max_length=0)
        result = parser.parse_args(["--argument", None])
        self.assertEquals(result.argument, None)
        result = parser.parse_args(["--argument", "12"])
        self.assertEquals(result.argument, "")

    def test_reads_string_with_whitespace_from_config(self):
        result = testargs.get_test_args()
        self.assertEquals(result.description, "my description with whitespace!")

class TestPositiveIntValidator(unittest.TestCase):
    def test_throws_if_not_int(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.PositiveIntValidator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "not an int"])

    def test_throws_if_not_positive_int(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.PositiveIntValidator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "-1234"])

    def test_accepts_positive_int(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.PositiveIntValidator)
        result = parser.parse_args(["--argument", "1234"])
        self.assertEquals(result.argument, 1234)

    def test_reads_token_duration_from_file_and_applies_default(self):
        result = testargs.get_test_args()
        self.assertEquals(result.sas_duration, 48)

class TestBlobNameValidator(unittest.TestCase):
    def test_accepts_none_for_output(self):
        parser = argparse.ArgumentParser(self)
        parser.add_argument("--argument", type=malibuargsactions.output_validator)
        result = parser.parse_args(["--argument", None])
        self.assertEquals(result.argument, None)

    def test_accepts_empty_string_for_output(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.output_validator)
        result = parser.parse_args(["--argument", ""])
        self.assertEquals(result.argument, None)

    def test_throws_if_empty_string_for_input(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.input_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", ""])

    def test_throws_if_string_too_long(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.input_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "x" * 1024 + "y"])

    def test_throws_if_non_standard_characters(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.output_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "/x;"])

    def test_accepts_with_standard_characters_for_output(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.output_validator)
        result = parser.parse_args(["--argument", "1234/AaZzYyXx.-_"])
        self.assertEquals(result.argument, "1234/AaZzYyXx.-_")

    def test_accepts_with_standard_characters_for_input(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.input_validator)
        result = parser.parse_args(["--argument", "1234/AaZzYyXx.-_"])
        self.assertEquals(result.argument, "1234/AaZzYyXx.-_")

    def test_throws_with_leading_slash_for_input(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.input_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "/my/blob.b"])

class TestRangeValidator(unittest.TestCase):
    def test_throws_on_empty_string(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", ""])

    def test_throws_on_just_colon(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "   :   "])

    def test_accepts_single_index_positive(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        result = parser.parse_args(["--argument", "10"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "asc")
        self.assertEquals(result.argument.top, 1)
        self.assertEquals(result.argument.skip, 10)

    def test_accepts_single_index_negative(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        result = parser.parse_args(["--argument", " -10"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "desc")
        self.assertEquals(result.argument.top, 1)
        self.assertEquals(result.argument.skip, 9)

    def test_accepts_open_range_left(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)

        result = parser.parse_args(["--argument", ":10"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "asc")
        self.assertEquals(result.argument.top, 10)
        self.assertEquals(result.argument.skip, None)

        result = parser.parse_args(["--argument", ":-10"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "desc")
        self.assertEquals(result.argument.top, None)
        self.assertEquals(result.argument.skip, 10)

    def test_accepts_open_range_right(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)

        result = parser.parse_args(["--argument", "10:"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "asc")
        self.assertEquals(result.argument.top, None)
        self.assertEquals(result.argument.skip, 10)

        result = parser.parse_args(["--argument", " -10:"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "desc")
        self.assertEquals(result.argument.top, 10)
        self.assertEquals(result.argument.skip, None)

    def test_accepts_positive_range(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        result = parser.parse_args(["--argument", "0:10"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "asc")
        self.assertEquals(result.argument.top, 10)
        self.assertEquals(result.argument.skip, 0)

    def test_accepts_negative_range(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        result = parser.parse_args(["--argument", " -10:-5"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "desc")
        self.assertEquals(result.argument.top, 5)
        self.assertEquals(result.argument.skip, 5)

    def test_accepts_zero_range(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        result = parser.parse_args(["--argument", " -10:-20"])
        self.assertIsNotNone(result.argument)
        self.assertEquals(result.argument.orderby, "desc")
        self.assertEquals(result.argument.top, 0)
        self.assertEquals(result.argument.skip, 20)

    def test_throws_on_unparseable_values(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "n:m"])

    def test_throws_on_different_signs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", action=malibuargsactions.RangeValidator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", " -4:4"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "4:-4"])

class TestNonEmptyStringType(unittest.TestCase):
    def test_throws_on_empty_string(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.nstr)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", ""])

    def test_throws_on_whitespace(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.nstr)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "      "])

    def test_accepts_string(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.nstr)
        result = parser.parse_args(["--argument", " s"])
        self.assertEquals(result.argument, "s")

class TestToBoolType(unittest.TestCase):
    def test_accepts_empty_string(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        result = parser.parse_args(["--argument", ""])
        self.assertIsNone(result.argument)

    def test_parses_true_and_false(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        result = parser.parse_args(["--argument", " tRuE "])
        self.assertTrue(result.argument)

        result = parser.parse_args(["--argument", "false"])
        self.assertFalse(result.argument)

    def test_throws_on_unparseable(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "whatever"])

class TestConfigFileReader(unittest.TestCase):

    def test_adds_values_from_config(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", action=malibuargsactions.ConfigFileReader)
        parser.add_argument("--access-key")
        parser.add_argument("--poll", type=malibuargsactions.to_bool)
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        result = parser.parse_args("--config tests/unittestconfig.txt".split())
        self.assertEquals(result.poll, True)
        self.assertIsNone(result.argument)
        self.assertEquals(result.config, "tests/unittestconfig.txt")

    def test_does_not_replace_values_from_command_line(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", action=malibuargsactions.ConfigFileReader)
        parser.add_argument("--access-key")
        parser.add_argument("--poll", type=malibuargsactions.to_bool)
        parser.add_argument("--emit-ref-confidence", type=str.lower, choices=["none", "gvcf"])
        parser.add_argument("--bgzip-output", type=malibuargsactions.to_bool)
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        result = parser.parse_args("--config tests/unittestconfig.txt --poll true --emit-ref-confidence gvcf --bgzip-output true".split())
        self.assertEquals(result.poll, True)
        self.assertEquals(result.emit_ref_confidence, "gvcf")
        self.assertEquals(result.bgzip_output, True)
        self.assertIsNone(result.argument)
        self.assertEquals(result.config, "tests/unittestconfig.txt")

    def test_does_not_run_configreader_for_a_value_from_config(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--command", action=malibuargsactions.ConfigFileReader)
        parser.add_argument("--access-key")
        parser.add_argument("--poll", type=malibuargsactions.to_bool)
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        result = parser.parse_args("--command tests/unittestconfig.txt --access-key moo".split())
        self.assertEquals(result.access_key, "moo")
        self.assertEquals(result.poll, True)
        self.assertIsNone(result.argument)
        self.assertEquals(result.command, "tests/unittestconfig.txt")

    def test_does_not_fail_on_nonexisting_config(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", action=malibuargsactions.ConfigFileReader)
        parser.add_argument("--access-key")
        parser.add_argument("--poll", type=malibuargsactions.to_bool)
        parser.add_argument("--argument", type=malibuargsactions.to_bool)
        result = parser.parse_args("--config whatever".split())
        self.assertIsNone(result.access_key)
        self.assertIsNone(result.poll)
        self.assertIsNone(result.argument)
        self.assertEquals(result.config, "whatever")

class TestNameDifference(unittest.TestCase):

    def test_matches_correctly(self):
        self.assertTrue(malibuargsactions.differ_in_at_most_one("", ""))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("", "a"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("a", ""))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("a", "a"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("a", "b"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("ab", "a"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("a", "aa"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("a", "ab"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("ba", "a"))
        self.assertTrue(malibuargsactions.differ_in_at_most_one("a", "ba"))

    def mismatches_correctly(self):
        self.assertFalse(malibuargsactions.differ_in_at_most_one("", "aa"))
        self.assertFalse(malibuargsactions.differ_in_at_most_one("aa", ""))
        self.assertFalse(malibuargsactions.differ_in_at_most_one("ab", "ba"))
        self.assertFalse(malibuargsactions.differ_in_at_most_one("aba", "baa"))

class TestReadGroupValidator(unittest.TestCase):
    def test_accepts_empty_string(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.read_group_validator)
        result = parser.parse_args(["--argument", ""])
        self.assertIsNone(result.argument)

    def test_throws_on_max_length_exceeded(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.read_group_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "@RG" * (malibuargsactions.MAX_READ_GROUP_LENGTH / 3 + 3)])

    def test_throws_on_bad_prefix(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.read_group_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "some string"])

    def test_throws_on_illegal_characters(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.read_group_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "@RG\tID:lalala;"])

    def test_accepts_value_correctly(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.read_group_validator)
        result = parser.parse_args(["--argument", "@RG\tID:lal ala\tSM:my sample"])
        self.assertEquals(result.argument, "@RG\\tID:lal ala\\tSM:my sample")


class TestProcessArgsValidator(unittest.TestCase):
    def test_throws_if_process_args_is_none(self):
        parser = argparse.ArgumentParser(self)
        parser.add_argument("--argument", type=malibuargsactions.process_args_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", None])

    def test_throws_if_bad_char_in_reference(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--argument", type=malibuargsactions.process_args_validator)
        with self.assertRaises(SystemExit):
            parser.parse_args(["--argument", "R=hg19m1-2"])

if __name__ == '__main__':
    unittest.main()
