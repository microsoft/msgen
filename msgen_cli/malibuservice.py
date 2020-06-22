# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Malibu Service API helper"""
import sys
import json
from time import sleep
try:
    import requests
except ImportError:
    print """You need to install the 'requests' library.
            Try: pip install requests"""
    sys.exit(code=1)
from requests.structures import CaseInsensitiveDict
from malibucommon import ORDER_ASC

def retry_policy(max_tries=45, start_delay=2, backoff_base=2, max_exp=5):
    """
    Decorator that retries service calls if a Timeout or Connection exception occurs
    or the status code is greater than 500.
    The default values result in 5 retries within a minute
    and subsequent retries at a 1.06 min interval for ~44 minutes
    """
    def decorator(func):
        """
        Decorator
        """
        def func_wrapper(*args, **kwargs):
            """
            Function wrapper
            """
            waitfor = start_delay
            retry = True
            tries = 0
            res = None
            while retry:
                try:
                    retry = tries < max_tries
                    res = func(*args, **kwargs)
                    if isinstance(res, int):
                        response_code = res
                    else:
                        response_code = int(res[0])
                    #handling 403 specifically, APIM returns this code when the service is down
                    #handling 429 specifically, APIM returns this code when throttling takes place
                    if response_code < 500 and response_code != 403 and response_code != 429:
                        return res
                    print "Response: {0}".format(response_code)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                    if not retry:
                        raise
                    print "Error: {0}".format(str(exc))
                if retry:
                    print "Retrying in {0}s, {1} of {2} retries ".format(str(waitfor),
                                                                         str(tries+1),
                                                                         str(max_tries))
                    sleep(waitfor)
                if tries < max_exp:
                    waitfor = waitfor * backoff_base
                tries = tries + 1
            return res
        return func_wrapper
    return decorator

class MalibuService(object):
    """ Malibu Service API helper class """

    def __init__(self, api_url, access_key):
        """ Constructor """
        self.api_url = api_url
        self.access_key = access_key

    @classmethod
    def handle_response(cls, response_code, response_data):
        """
        Handles service response.
        Returns the message, status or workflow id, if applicable
        """

        client_error = response_code >= 400 and response_code < 500
        success = response_code >= 200 and response_code < 300

        workflow = CaseInsensitiveDict({"Message":"", "Id": 0, "Status": 0})

        if client_error or success:
            try:
                response_content = json.loads(response_data)
                workflow.update(response_content)
            except ValueError:
                workflow["Message"] = "Invalid response content"
        else:
            workflow["Message"] = "{0}: Internal server error".format(response_code)

        return workflow

    @classmethod
    def get_headers(cls, access_key):
        """ Gets request headers """
        headers = {"content-type": "application/json",
                   "User-Agent": "Microsoft Genomics Command-line Client",
                   "Ocp-Apim-Subscription-Key": access_key}
        return headers

    def get_workflow_url(self, workflow_id):
        """ parses workflow status url """
        return self.api_url + str(workflow_id)

    @classmethod
    def get_workflow_item_request_body(cls,
                                       process_name,
                                       process_args,
                                       input_storage_account_type,
                                       output_storage_account_type,
                                       input_dictionary,
                                       output_dictionary,
                                       description,
                                       optional_args,
                                       workflow_class,
                                       ignore_azure_region):

        """ parses the HTTP request's body to create a workflow item """
        body = {"Process": process_name,
                "ProcessArgs": process_args,
                "Description": description,
                "InputStorageType": input_storage_account_type,
                "OutputStorageType": output_storage_account_type,
                "InputArgs": input_dictionary,
                "OutputArgs": output_dictionary,
                "OptionalArgs": optional_args,
                "WorkflowClass": workflow_class,
                "IgnoreAzureRegion": ignore_azure_region}

        return body

    @retry_policy()
    def create_workflow_item(self, process_name, process_args,
                             input_storage_account_type, output_storage_account_type,
                             input_dictionary, output_dictionary,
                             description, optional_args, workflow_class, ignore_azure_region):
        """ submits POST HTTP request to create a workflow item """
        body = MalibuService.get_workflow_item_request_body(
            process_name,
            process_args,
            input_storage_account_type,
            output_storage_account_type,
            input_dictionary,
            output_dictionary,
            description,
            optional_args,
            workflow_class,
            ignore_azure_region)
        headers = MalibuService.get_headers(self.access_key)

        response = requests.post(self.api_url,
                                 data=json.dumps(body),
                                 headers=headers,
                                 timeout=300)

        response_code = response.status_code
        workflow = MalibuService.handle_response(response_code, response.content)

        return response_code, workflow
    @retry_policy()
    def cancel_workflow_item(self, workflow_id):
        """ submits a DELETE HTTP request to cancel a workflow item """
        headers = MalibuService.get_headers(self.access_key)
        url = self.get_workflow_url(workflow_id)
        response = requests.delete(url,
                                   headers=headers)
        response_code = response.status_code
        workflow = MalibuService.handle_response(response_code, response.content)
        #return response code and workflow info
        return response_code, workflow
    @retry_policy()
    def get_workflow_list(self, in_range, with_description, with_process, outcome):
        """ submits a GET HTTP request to get the list of workflow items
        for the current account """
        odata_args = {}
        if in_range is not None:
            if in_range.orderby is not None:
                odata_args["$orderby"] = "CreatedDate " + in_range.orderby
            if in_range.skip is not None:
                odata_args["$skip"] = in_range.skip
            if in_range.top is not None:
                odata_args["$top"] = in_range.top
        else:
             # by default output oldest -> most recent
            odata_args["$orderby"] = "CreatedDate " + ORDER_ASC
        filters = []
        if with_description is not None:
            filters.append("substringof('{0}', Description)".format(with_description))
        if with_process is not None:
            filters.append("substringof('{0}', Process)".format(with_process))
        if outcome is not None:
            filters.append("Status eq '{0}'".format(50000 if outcome == "fail" else 20000))
        if filters:
            odata_args["$filter"] = " and ".join(filters)
        headers = MalibuService.get_headers(self.access_key)
        response = requests.get(self.api_url, headers=headers, params=odata_args)
        response_code = response.status_code

        workflow_data = ""
        try:
            workflow_data = json.loads(response.text)
        except ValueError:
            workflow_data = response.text

        return response_code, workflow_data
    @retry_policy()
    def get_workflow_status(self, workflow_id):
        """ submits a GET HTTP request to retrieve the status of a workflow """
        headers = MalibuService.get_headers(self.access_key)
        url = self.get_workflow_url(workflow_id)

        response = requests.get(url, headers=headers)

        response_code = response.status_code

        workflow = MalibuService.handle_response(response_code, response.text)

        return response_code, workflow

class ClientHTTPException(BaseException):
    """Client HTTP exception"""
    pass
