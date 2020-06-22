# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Test workflow functionality"""
import sys
import unittest
from collections import OrderedDict
from StringIO import StringIO
from datetime import datetime
import testargs
import msgen_cli.malibuworkflow as malibuworkflow
import msgen_cli.datatransfer as datatransfer

class TestMalibuWorkflow(unittest.TestCase):
    """
    Malibu workflow test scenarios
    """
    @unittest.skip("Not a unit test.")
    def test_submit_and_status(self):
        """Submits a workflow item, assuming storage inputs
           no download"""
        args = testargs.get_test_args()
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow_id = workflow.post_workflow_blocking()

        self.assertTrue(workflow_id > 0)
        workflow.get_workflow_status()

        self.assertTrue(workflow.current_exit_status > 1)

    @unittest.skip("Not a unit test.")
    def test_lists(self):
        """Lists workflow items"""
        args = testargs.get_test_args()
        workflow = malibuworkflow.WorkflowExecutor(args)

        workflow.list_workflows()

        self.assertTrue(workflow.current_exit_status == 0)


    def test_exit_status_states(self):
        """test exit status by result, response code and
        workflow status"""
        args = testargs.get_test_args()
        result = 1
        response = 200
        status = 1000
        workflow = malibuworkflow.WorkflowExecutor(args)

        #when only result is set, all other parameters are not considered
        result = 1
        workflow.set_exit_code(result, response, status)
        self.assertTrue(workflow.current_exit_status == result)

        #response code not in the mapping dict, default to error"
        response = 500
        self.assertTrue(response not in workflow.exit_status_by_response)
        workflow.set_exit_code(None, response, None)
        self.assertTrue(workflow.current_exit_status == 1000)

        #response code only
        response = 200
        workflow.set_exit_code(None, response, None)
        self.assertTrue(
            workflow.current_exit_status ==
            workflow.exit_status_by_response[response][1])

        #when response code is set to a value other than 200, takes precedent
        response = 400
        workflow.set_exit_code(None, response, status)
        self.assertTrue(
            workflow.current_exit_status ==
            workflow.exit_status_by_response[response][1])

        #when response is succesful, exit code is set by workflow_status
        response = 200
        status = 20000
        workflow.set_exit_code(None, response, status)
        self.assertTrue(
            workflow.current_exit_status ==
            workflow.exit_status_by_workflow_status[status][1])

    @unittest.skip("Not a unit test.")
    def test_submit_and_cancel_np(self):
        """Submits a workflow item, assuming storage inputs
           no download"""
        args = testargs.get_test_args()
        args.poll = False

        workflow = malibuworkflow.WorkflowExecutor(args)

        workflow_id = workflow.post_workflow_blocking()

        workflow.cancel_workflow()

        self.assertTrue(workflow_id > 0)

    @unittest.skip("Not a unit test.")
    def test_submit_and_cancel(self):
        """Submits a workflow item, assuming storage inputs
           no download"""
        args = testargs.get_test_args()

        workflow = malibuworkflow.WorkflowExecutor(args)

        workflow_id = workflow.post_workflow_blocking()

        workflow.cancel_workflow()

        self.assertTrue(workflow_id > 0)
        self.assertTrue(workflow.current_exit_status == 1000)

    def test_display_status_with_message_and_response(self):
        """
        display_status prints a line like the following:
        [01/18/2017 17:56:28] - Message: This is unacceptable  Status Code: None  Response Code: 400
        """
        args = testargs.get_test_args()
        workflow = malibuworkflow.WorkflowExecutor(args)

        real_stdout = sys.stdout
        try:
            string_stdout = StringIO()
            sys.stdout = string_stdout
            workflow.display_status({"Message": "This is unacceptable"}, response_code=400)
            printed = string_stdout.getvalue()
            self.assertTrue("This is unacceptable" in printed)
            self.assertTrue("400" in printed)
        finally:
            sys.stdout = real_stdout

    def test_display_status_workflow_short(self):
        """
        display_status prints a line like the following:
        [01/18/2017 17:58:00 - Workflow ID: 1]: Message: Queued
        """
        args = testargs.get_test_args()
        workflow = malibuworkflow.WorkflowExecutor(args)

        response_workflow = {"Id": 1, "Status": 1000, "Process": "snapgatk", "Description": "Tru la la"}

        real_stdout = sys.stdout
        try:
            string_stdout = StringIO()
            sys.stdout = string_stdout
            workflow.display_status(response_workflow, short=True)
            printed = string_stdout.getvalue()
            self.assertTrue("Workflow ID: 1" in printed)
            self.assertTrue("Message: Queued" in printed)
            self.assertFalse("snapgatk" in printed)
            self.assertFalse("Tru la la" in printed)
        finally:
            sys.stdout = real_stdout

    def test_display_status_workflow_long(self):
        """
        display_status prints lines like the following:
        [01/18/2017 17:58:35 - Workflow ID: 1]: Message: Queued
	        Process: snapgatk
	        Description: Tru la la
        """
        args = testargs.get_test_args()
        workflow = malibuworkflow.WorkflowExecutor(args)

        response_workflow = {"Id": 1, "Status": 1000, "Process": "snapgatk", "Description": "Tru la la"}

        real_stdout = sys.stdout
        try:
            string_stdout = StringIO()
            sys.stdout = string_stdout
            workflow.display_status(response_workflow, short=False)
            printed = string_stdout.getvalue()
            self.assertTrue("Workflow ID: 1" in printed)
            self.assertTrue("Message: Queued" in printed)
            self.assertTrue("snapgatk" in printed)
            self.assertTrue("Tru la la" in printed)
        finally:
            sys.stdout = real_stdout

    def test_wall_clock_time_returns_correct_measurement_for_under_24_hrs(self):
        end_date = "2017-01-19T00:59:34.1374134+00:00"
        start_date = datetime(year=2017, month=1, day=18, hour=23, minute=57, second=31) 
        end_str, hours, minutes, seconds = malibuworkflow.WorkflowExecutor.workflow_wall_clock_endtime(end_date, start_date)

        self.assertEquals(1, hours)
        self.assertEquals(2, minutes)
        self.assertEquals(3, seconds)
        self.assertTrue(isinstance(hours, int))
        self.assertTrue(isinstance(minutes, int))
        self.assertTrue(isinstance(seconds, int))

    def test_wall_clock_time_returns_correct_measurement_for_24_hrs(self):
        end_date = "2017-01-19T00:59:34.1374134+00:00"
        start_date = datetime(year=2017, month=1, day=18, hour=0, minute=59, second=34) 
        end_str, hours, minutes, seconds = malibuworkflow.WorkflowExecutor.workflow_wall_clock_endtime(end_date, start_date)

        self.assertEquals(24, hours)
        self.assertEquals(0, minutes)
        self.assertEquals(0, seconds)
        self.assertTrue(isinstance(hours, int))
        self.assertTrue(isinstance(minutes, int))
        self.assertTrue(isinstance(seconds, int))

    def test_wall_clock_time_returns_correct_measurement_for_over_24_hrs(self):
        end_date = "2017-01-19T00:59:34.1374134+00:00"
        start_date = datetime(year=2017, month=1, day=17, hour=23, minute=57, second=31) 
        end_str, hours, minutes, seconds = malibuworkflow.WorkflowExecutor.workflow_wall_clock_endtime(end_date, start_date)

        self.assertEquals(25, hours)
        self.assertEquals(2, minutes)
        self.assertEquals(3, seconds)
        self.assertTrue(isinstance(hours, int))
        self.assertTrue(isinstance(minutes, int))
        self.assertTrue(isinstance(seconds, int))

    def test_transform_workflow_for_output_with_finished_workflow(self):
        workflow = {
            "Id": 3167,
            "Status": 20000,
            "CreatedDate": "2017-02-08T00:57:16.3403168+00:00",
            "EndDate": "2017-02-08T01:23:37.0531197+00:00",
            "FailureCode": 0,
            "Message": None,
            "Description": "process_args",
            "Process": "snapgatk-20170207_1"
        }
        expected = OrderedDict()
        expected["Workflow ID"] = "3167"
        expected["Status"] = "Completed successfully"
        expected["Message"] = ""
        expected["Process"] = "snapgatk-20170207_1"
        expected["Description"] = "process_args"
        expected["Created Date"] = "Wed, 08 Feb 2017 00:57:16 GMT"
        expected["End Date"] = "Wed, 08 Feb 2017 01:23:37 GMT"
        expected["Wall Clock Time"] = "0h 26m 21s"
        expected["Bases Processed"] = ""
        args = testargs.get_test_args()
        workflow_executor = malibuworkflow.WorkflowExecutor(args)
        transformed = workflow_executor.transform_workflow_for_output(workflow)
        self.assertDictEqual(transformed, expected)

    def test_transform_workflow_formats_gbases_correctly(self):
        workflow = {
            "Id": 3167,
            "Status": 20000,
            "CreatedDate": "2017-02-08T00:57:16.3403168+00:00",
            "EndDate": "2017-02-08T01:23:37.0531197+00:00",
            "FailureCode": 0,
            "Message": None,
            "Description": "process_args",
            "Process": "snapgatk-20170207_1",
            "BasesProcessed": "127434222576"
        }
        expected = OrderedDict()
        expected["Workflow ID"] = "3167"
        expected["Status"] = "Completed successfully"
        expected["Message"] = ""
        expected["Process"] = "snapgatk-20170207_1"
        expected["Description"] = "process_args"
        expected["Created Date"] = "Wed, 08 Feb 2017 00:57:16 GMT"
        expected["End Date"] = "Wed, 08 Feb 2017 01:23:37 GMT"
        expected["Wall Clock Time"] = "0h 26m 21s"
        expected["Bases Processed"] = "127,434,222,576 (127 GBase)"
        args = testargs.get_test_args()
        workflow_executor = malibuworkflow.WorkflowExecutor(args)
        transformed = workflow_executor.transform_workflow_for_output(workflow)
        self.assertDictEqual(transformed, expected)

    def test_transform_workflow_for_output_with_unfinished_workflow(self):
        workflow = {
            "Id": 3167,
            "Status": 1000,
            "CreatedDate": "2017-02-08T00:57:16.3403168+00:00",
            "EndDate": None,
            "FailureCode": 0,
            "Message": None,
            "Description": None,
            "Process": "snapgatk-20170207_1"
        }
        args = testargs.get_test_args()
        workflow_executor = malibuworkflow.WorkflowExecutor(args)
        transformed = workflow_executor.transform_workflow_for_output(workflow)
        self.assertIsNotNone(transformed)
        self.assertEquals(transformed["Workflow ID"], "3167")
        self.assertEquals(transformed["Status"], "Queued")
        self.assertEquals(transformed["Message"], "")
        self.assertEquals(transformed["Description"], "")
        self.assertEquals(transformed["Process"], "snapgatk-20170207_1")
        self.assertEquals(transformed["Created Date"], "Wed, 08 Feb 2017 00:57:16 GMT")
        self.assertEquals(transformed["End Date"], "")
        self.assertTrue(transformed["Wall Clock Time"]) # not None and not an empty string

    def test_transform_workflow_for_None(self):
        args = testargs.get_test_args()
        workflow_executor = malibuworkflow.WorkflowExecutor(args)
        transformed = workflow_executor.transform_workflow_for_output(None)
        self.assertIsNotNone(transformed)
        self.assertTrue(len(transformed.keys()) == 0)

    def test_get_input_output_dict_handles_one_file(self):
        args = testargs.get_test_args()
        args.input_blob_name_1 = ["file.bam"]
        args.input_blob_name_2 = []
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        inputs, outputs = workflow.get_input_and_output_dict()
        self.assertEquals(inputs["BLOBNAMES"], "file.bam,")

    def test_get_input_output_dict_handles_one_file_with_sas(self):
        args = testargs.get_test_args()
        args.input_blob_name_1 = ["file.bam?sas"]
        args.input_blob_name_2 = []
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        inputs, outputs = workflow.get_input_and_output_dict()
        self.assertEquals(inputs["BLOBNAMES"], "file.bam,")

    def test_get_input_output_dict_handles_two_files(self):
        args = testargs.get_test_args()       
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        inputs, outputs = workflow.get_input_and_output_dict()
        self.assertEquals(inputs["BLOBNAMES"], "chr21-10k_1.fq.gz,chr21-10k_2.fq.gz,")

    def test_get_input_output_dict_handles_two_files_with_sas(self):
        args = testargs.get_test_args()       
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        inputs, outputs = workflow.get_input_and_output_dict()
        self.assertEquals(inputs["BLOBNAMES"], "chr21-10k_1.fq.gz,chr21-10k_2.fq.gz,")

    def test_get_input_output_dict_handles_multiple_files(self):
        args = testargs.get_test_args()
        args.input_blob_name_1 = ["chr21-10k_1.fq.gz", "chr22-10k_1.fq.gz"]
        args.input_blob_name_2 = ["chr21-10k_2.fq.gz", "chr22-10k_2.fq.gz"]
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        inputs, outputs = workflow.get_input_and_output_dict()
        self.assertEquals(inputs["BLOBNAMES"], "chr21-10k_1.fq.gz,chr21-10k_2.fq.gz,chr22-10k_1.fq.gz,chr22-10k_2.fq.gz,")


    def test_get_input_output_dict_handles_multiple_files_with_sas(self):
        args = testargs.get_test_args()
        args.input_blob_name_1 = ["chr21-10k_1.fq.gz?sas", "chr22-10k_1.fq.gz?sas"]
        args.input_blob_name_2 = ["chr21-10k_2.fq.gz?sas", "chr22-10k_2.fq.gz?sas"]
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        inputs, outputs = workflow.get_input_and_output_dict()
        self.assertEquals(inputs["BLOBNAMES"], "chr21-10k_1.fq.gz,chr21-10k_2.fq.gz,chr22-10k_1.fq.gz,chr22-10k_2.fq.gz,")

    def test_construct_optional_args_returns_empty_dictionary_without_args(self):
        args = testargs.get_test_args()
        args.bqsr_enabled = None
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        optional_args = workflow.construct_optional_args()
        self.assertDictEqual(optional_args, {})

    def test_construct_optional_args_returns_nonempty_dictionary(self):
        args = testargs.get_test_args()
        args.bqsr_enabled = True
        workflow = malibuworkflow.WorkflowExecutor(args)
        workflow.datatransfer = FakeDataTransfer(None)

        optional_args = workflow.construct_optional_args()
        self.assertDictEqual(optional_args, {"BQSR": True})

        args.bqsr_enabled = False
        optional_args = workflow.construct_optional_args()
        self.assertDictEqual(optional_args, {"BQSR": False})

class FakeDataTransfer(datatransfer.AzureDataTransfer):
    def __init__(self, storage_account_info):
        self.input_container = "in"
        self.output_container = "out"

    def create_input_blob_sas_url(self, blob_name, sas_token_hours):
        return blob_name + "?sas"

    def create_output_sas(self, sas_token_hours):
        return self.output_container + "?sas"

if __name__ == '__main__':
    unittest.main()
