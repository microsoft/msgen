# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Test service functions"""
import unittest
import testargs
import requests
import msgen_cli.malibuservice as malibuservice
import msgen_cli.malibuworkflow as malibuworkflow
import msgen_cli.malibucommon as malibucommon

class RetryPolicyTest(unittest.TestCase):
    def test_retry_policy(self):

        @malibuservice.retry_policy(5, 1, 1, 1)
        def service_call(good_response, bad_response, num_of_bad, counter, exception=None):
            """function that simulates responses and exceptions"""
            while counter[0] < num_of_bad:
                counter[0] = counter[0] + 1
                if exception is not None:
                    raise exception # pylint: disable-msg=E0702
                return bad_response, 0
            return good_response, 0

        ##success on second retry
        retries = [1]
        response = service_call(200, 503, 3, retries)
        self.assertTrue(response[0] == 200)

        ##failure after 5 retries (1 call and 5 retries)
        retries = [1]
        response = service_call(200, 503, 7, retries)
        self.assertTrue(response[0] == 503)

        ##success on second retry
        retries = [1]
        ex = requests.exceptions.Timeout()
        response = service_call(200, 503, 3, retries, ex)
        self.assertTrue(response[0] == 200)

        ##failure after 6 timeouts (first call, timesout and 5 retries that all timeout)
        retries = [1]
        self.assertRaises(requests.exceptions.Timeout,
                          lambda: service_call(200, 503, 7, retries, ex))

        ##success on second connection error
        retries = [1]
        ex = requests.exceptions.ConnectionError()
        response = service_call(200, 503, 3, retries, ex)
        self.assertTrue(response[0] == 200)

        ##failure after 6 connection errors
        retries = [1]
        self.assertRaises(requests.exceptions.ConnectionError,
                          lambda: service_call(200, 503, 7, retries, ex))


@unittest.skip("Not a unit test.")
class MalibuServiceTest(unittest.TestCase):
    """ test cases for the malibu service class """
    def setUp(self):
        args = testargs.get_test_args()
        url = malibucommon.get_api_url_from_base(args.api_url_base)
        self.service = malibuservice.MalibuService(
            url, args.access_key)

        #create an instace of the worflow to set the dictionaries
        workflow = malibuworkflow.WorkflowExecutor(args)
        self.input_dic, self.output_dic = workflow.get_input_and_output_dict()

        self.process_name = args.process_name
        self.process_args = args.process_args
        self.storage_account_type = "AZURE_BLOCK_BLOB"
        self.description = None
        self.workflow_class = None

    def test_create_and_cancel(self):
        """Create and cancel test case"""
        response_code, workflow = self.service.create_workflow_item(
            self.process_name,
            self.process_args,
            self.storage_account_type,
            self.storage_account_type,
            self.input_dic,
            self.output_dic,
            self.description,
            None,
            self.workflow_class,
            False)

        self.assertTrue(response_code == 200 and
                        workflow["Id"] > 0)

        response_code, workflow = self.service.cancel_workflow_item(workflow["Id"])

        self.assertTrue(response_code == 200)
        self.assertTrue(workflow["Message"] is None)
        self.assertTrue(workflow["Status"] == 58000 or workflow["Status"] == 60000)

    def test_create_and_get_status(self):
        """Tests creation and status"""
        response_code, workflow = self.service.create_workflow_item(
            self.process_name,
            self.process_args,
            self.storage_account_type,
            self.storage_account_type,
            self.input_dic, self.output_dic,
            self.description,
            None,
            self.workflow_class,
            False)

        self.assertTrue(response_code == 200 and workflow["Id"] > 0)

        response_code, workflow = self.service.get_workflow_status(workflow["Id"])

        print "--> {0} {1}".format(workflow["Status"], workflow["Message"])

        self.assertTrue(response_code == 200)

    def test_list_my_workflows(self):
        """tests getting a list of workflow items"""
        response_code, workflow_data = self.service.get_workflow_list(None, None, None, None)

        self.assertTrue(response_code == 200 and workflow_data is not None)
        # description may be None, but Process can't be
        self.assertTrue(all("Description" in w and w["Process"] for w in workflow_data))

    def test_create_workflow_item(self):
        """tests creating a workflow item"""
        response_code, workflow = self.service.create_workflow_item(
            self.process_name,
            self.process_args,
            self.storage_account_type,
            self.storage_account_type,
            self.input_dic,
            self.output_dic,
            self.description,
            None,
            self.workflow_class,
            False)

        self.assertTrue(response_code == 200 and workflow["Id"] > 0)

    def test_create_workflow_item_with_description(self):
        """tests creating a workflow item"""
        response_code, workflow = self.service.create_workflow_item(
            self.process_name,
            self.process_args,
            self.storage_account_type,
            self.storage_account_type,
            self.input_dic,
            self.output_dic,
            "my description",
            None,
            self.workflow_class,
            False)

        self.assertTrue(response_code == 200 and workflow["Id"] > 0)
        self.assertTrue(workflow["Description"] == "my description")

if __name__ == '__main__':
    unittest.main()
