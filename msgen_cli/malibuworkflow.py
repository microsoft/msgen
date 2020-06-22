# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""File for all workflow related functionality"""
import csv
import sys
import time
from collections import OrderedDict
from datetime import datetime
from itertools import izip_longest
try:
    import requests
except ImportError:
    print "You need to install the 'requests' library. Try: pip install requests"
    sys.exit(code=1)

import malibucommon
import malibuservice
import datatransfer

class WorkflowExecutor(object):
    """ Main class for working with workflows """
    def __init__(self, args_output):

        """ Constructor """
        self.args_output = args_output
        malibu_url = malibucommon.get_api_url_from_base(
            self.args_output.api_url_base)

        self.service = malibuservice.MalibuService(
            malibu_url,
            self.args_output.access_key)

        storage_info = args_output.get_storage_accounts_info()

        self.datatransfer = datatransfer.AzureDataTransfer(storage_info)

        #set exit status code
        self.current_exit_status = None
        self.exit_status_by_result = {
            0:("Success", 0),
            1:("Failure", 1),
            2:("Temporary failure", 100)}

        self.exit_status_by_response = {
            200:("Success", 0),
            400:("Temporary failure", 100),
            401:("Unauthorized", 1000),
            405:("Not allowed", 1000)}

        #workflow status code:{name,sys_exit_code}
        self.exit_status_by_workflow_status = {
            1000:("Queued", 10),
            10000:("In progress", 20),
            20000:("Completed successfully", 0),
            50000:("Failed", 1000),
            58000:("Cancellation requested", 1000),
            60000:("Cancelled", 1000)}

    def display_status(self, workflow, response_code=None, short=True):
        """ Displays status of workflow """
        display_message = "NA"
        if workflow.get("Message"):
            display_message = workflow["Message"]
        elif workflow.get("Status") in self.exit_status_by_workflow_status:
            display_message = self.exit_status_by_workflow_status[workflow["Status"]][0]

        print_template = "[{0}] - Message: {1}  Status Code: {2}"
        msg = print_template.format(
            time.strftime("%m/%d/%Y %H:%M:%S"),
            display_message,
            workflow.get("Status"))

        if response_code:
            msg += "  Response Code: {0}".format(response_code)

        if workflow.get("Id") > 0:
            print_template = "[{0} - Workflow ID: {1}]: Message: {2}"
            msg = print_template.format(
                time.strftime("%m/%d/%Y %H:%M:%S"),
                str(workflow["Id"]),
                display_message)
            if not short:
                msg += "\n\tProcess: {0}\n\tDescription: {1}".format(workflow.get("Process"), workflow.get("Description"))

        print msg
        sys.stdout.flush()

    def display_error(self, exception, response_code, status_code):
        """ Display errors  """
        workflow_status = "NA"
        if status_code in self.exit_status_by_workflow_status:
            workflow_status = self.exit_status_by_workflow_status[status_code][0]

        message = "Exception: {0}, Response Code {1}, Status {2} "
        print message.format(str(exception),
                             str(response_code),
                             workflow_status)
    @classmethod
    def workflow_wall_clock_endtime(cls, end_date, created_date_object):
        """ Calculates the end time of a workflow item """
        utc_now = datetime.utcnow()
        time_delta = utc_now - created_date_object
        return_end_date = ""

        if end_date is not None and end_date != "":
            end_date_parts = str(end_date).split(".")
            end_date_object = datetime.strptime(end_date_parts[0], '%Y-%m-%dT%H:%M:%S')
            time_delta = end_date_object-created_date_object
            return_end_date = str(end_date)

        base_seconds = int(time_delta.total_seconds())
        hours, remainder = divmod(base_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return return_end_date, hours, minutes, seconds

    def post_workflow(self):
        """Posts a new workflow to the service"""

        workflow_id = self.post_workflow_blocking()
        if not self.args_output.poll or workflow_id <= 0:
            return

        self.poll_workflow_status_blocking(workflow_id)

    def post_workflow_blocking(self):
        """Posts a new workflow to the service and blocks"""

        input_dic, output_dic = self.get_input_and_output_dict()

        try:
            optional_args = self.construct_optional_args()
            response_code, workflow = self.service.create_workflow_item(
                self.args_output.process_name,
                self.args_output.process_args,
                self.args_output.input_storage_account_type,
                self.args_output.output_storage_account_type,
                input_dic,
                output_dic,
                self.args_output.description,
                optional_args,
                self.args_output.workflow_class,
                self.args_output.ignore_azure_region)

            self.set_exit_code(None, response_code)
            if not workflow.get("Message"):
                workflow["Message"] = "Successfully submitted"

            self.display_status(workflow, response_code, short=False)
            self.args_output.workflow_id = workflow.get("Id", 0)
            return self.args_output.workflow_id

        except requests.exceptions.ConnectionError as exc:
            print ("Could not connect to Malibu REST API."
                   "  Please review the api_url_base setting in config.txt,"
                   " and check your network settings.")
            print "Exception: {0}".format(str(exc))
            self.set_exit_code(2)

    def construct_optional_args(self):
        """ Create a dictionary of optional arguments that can modify process execution """
        optional_args = {}
        if self.args_output.bqsr_enabled is not None:
            optional_args["BQSR"] = self.args_output.bqsr_enabled
        if self.args_output.read_group is not None:
            optional_args["ReadGroupLine"] = self.args_output.read_group
        if self.args_output.emit_ref_confidence is not None:
            optional_args["GatkEmitRefConfidence"] = self.args_output.emit_ref_confidence
        if self.args_output.bgzip_output is not None:
            optional_args["BgzipOutput"] = self.args_output.bgzip_output
        return optional_args

    def poll_workflow_status_blocking(self, workflow_id=0, success_status=20000):
        """ Polls the status of submitted workflow """
        poll_interval_seconds = 60
        if workflow_id == 0:
            workflow_id = self.args_output.workflow_id
        poll = True
        response_code = 0
        status_code = 0
        try:
            while poll:
                response_code, workflow = self.service.get_workflow_status(workflow_id)
                status_code = workflow.get("Status")
                self.display_status(workflow)
                self.set_exit_code(None, response_code, status_code)

                success = status_code == success_status
                failure = status_code == 50000 or status_code == 60000

                poll = not success and not failure

                if poll:
                    time.sleep(poll_interval_seconds)

        except Exception as exc:
            self.display_error(exc, response_code, status_code)

    def get_workflow_status(self):
        """ Gets the workflow status and sets the corresponding exit code """
        workflow_id = self.args_output.workflow_id
        status_code = 0
        response_code = 0
        try:
            response_code, workflow = self.service.get_workflow_status(workflow_id)
            status_code = workflow.get("Status", status_code)
            self.display_status(workflow, short=False)
            self.set_exit_code(None, None, status_code)

        except Exception as exc:
            self.display_error(exc, response_code, status_code)
            self.set_exit_code(1)

    def cancel_workflow(self):
        """ Cancels an existing workflow """
        workflow_id = self.args_output.workflow_id
        response_code = 0
        try:
            response_code, workflow = self.service.cancel_workflow_item(workflow_id)
            cancellation_response_code = response_code
            self.set_exit_code(None, response_code)
            response_code, workflow = self.service.get_workflow_status(workflow_id)
            self.display_status(workflow, short=False)
            self.set_exit_code(None, response_code, workflow.get("Status", 0))

        except Exception as exc:
            self.display_error(exc, response_code, None)
            self.set_exit_code(1)
            return

        if not self.args_output.poll or workflow_id <= 0 or 400 <= cancellation_response_code < 500:
            return

        self.poll_workflow_status_blocking(0, 60000)

    def list_workflows(self):
        """ Lists existing workflows """
        response_code = 0
        try:
            response_code, workflow_data = self.service.get_workflow_list(self.args_output.in_range,
                                                                          self.args_output.with_description,
                                                                          self.args_output.with_process,
                                                                          self.args_output.outcome)
            if not isinstance(workflow_data, list):
                if hasattr(workflow_data, "message"):
                    error = workflow_data["message"]
                else:
                    error = workflow_data
                raise Exception("Service returned an error: {0}".format(error))
            count = len(workflow_data)
            if self.args_output.in_range is not None and self.args_output.in_range.orderby == malibucommon.ORDER_DESC:
                workflow_data = reversed(workflow_data)
            if self.args_output.output_file is not None:
                out_file, close = open(self.args_output.output_file, mode="w"), True
            else:
                out_file, close = sys.stdout, False
            if self.args_output.export_to == "csv":
                self.print_csv(workflow_data, out_file)
            else:
                self.print_text(workflow_data, out_file, count)
            out_file.flush()
            if close:
                out_file.close()

            self.set_exit_code(None, response_code)

        except Exception as exc:
            self.display_error(exc, response_code, None)
            self.set_exit_code(1)

    def print_csv(self, workflow_data, out_file):
        """Output a list of workflows in CSV to a file"""
        rows = [self.transform_workflow_for_output(w) for w in workflow_data]
        header = rows[0].keys() if rows else []
        writer = csv.DictWriter(out_file, header, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    def print_text(self, workflow_data, out_file, count):
        """Output a list of workflows in plain text to a file"""
        out_file.write("\nWorkflow List\n-------------\nTotal Count  : {0}\n\n".format(count))
        for workflow in workflow_data:
            workflow = self.transform_workflow_for_output(workflow)
            out_file.write("\n".join("{0:<15} : {1}".format(k, v) for (k, v) in workflow.iteritems()) + "\n\n")

    def transform_workflow_for_output(self, workflow):
        """Transform workflow fields for output"""
        if workflow is None:
            return OrderedDict()
        workflow_id = self.get_str_value(workflow, "Id")
        message = self.get_str_value(workflow, "Message")
        description = self.get_str_value(workflow, "Description")
        process = self.get_str_value(workflow, "Process")
        created_date = self.get_str_value(workflow, "CreatedDate")
        end_date = self.get_str_value(workflow, "EndDate")
        status = self.exit_status_by_workflow_status[workflow["Status"]][0]
        
        created_date_object = datetime.strptime(created_date.split(".", 1)[0], "%Y-%m-%dT%H:%M:%S")
        end_date, hours, minutes, seconds = WorkflowExecutor.workflow_wall_clock_endtime(end_date, created_date_object)
        wall_time = "{0}h {1}m {2}s".format(hours, minutes, seconds)
        end_date_object = datetime.strptime(end_date.split(".", 1)[0], "%Y-%m-%dT%H:%M:%S") if end_date else None

        raw_bases = self.get_str_value(workflow, "BasesProcessed")
        if raw_bases:
            number_bases = long(raw_bases)
            gbases = number_bases // 1000000000
            processed_bases = "{0:,d} ({1:,d} GBase)".format(number_bases, gbases)
        else:
            processed_bases = ""

        return OrderedDict([
            ("Workflow ID", workflow_id),
            ("Status", status),
            ("Message", message),
            ("Process", process),
            ("Description", description),
            ("Created Date", malibucommon.format_rfc1123(created_date_object)),
            ("End Date", malibucommon.format_rfc1123(end_date_object)),
            ("Wall Clock Time", wall_time),
            ("Bases Processed", processed_bases)])

    def get_input_and_output_dict(self):
        """ gets the input dictionary with the service parameters """
        input_dic = dict()
        self.add_key_value(input_dic, "ACCOUNT",
                           self.args_output.input_storage_account_name, False)
        self.add_key_value(input_dic, "CONTAINER",
                           self.datatransfer.input_container, False)
        for blob1, blob2 in izip_longest(self.args_output.input_blob_name_1, self.args_output.input_blob_name_2):
            if blob1:
                if "?" in blob1:
                    # SAS token has been included in blobname
                    blob_name_parts = blob1.split("?")  
                    self.add_key_value(input_dic, "BLOBNAMES", blob_name_parts[0], True)
                    self.add_key_value(input_dic,
                                       "BLOBNAMES_WITH_SAS",
                                       blob1,
                                       True)
                else:
                    self.add_key_value(input_dic, "BLOBNAMES", blob1, True)
                    self.add_key_value(input_dic,
                                       "BLOBNAMES_WITH_SAS",
                                       self.datatransfer.create_input_blob_sas_url(blob1, self.args_output.sas_duration),
                                       True)
            if blob2:
                if "?" in blob2:
                    # SAS token has been included in blobname
                    blob_name_parts = blob2.split("?")  
                    self.add_key_value(input_dic, "BLOBNAMES", blob_name_parts[0], True)
                    self.add_key_value(input_dic,
                                       "BLOBNAMES_WITH_SAS",
                                       blob2,
                                       True)
                else:
                    self.add_key_value(input_dic, "BLOBNAMES", blob2, True)
                    self.add_key_value(input_dic,
                                       "BLOBNAMES_WITH_SAS",
                                       self.datatransfer.create_input_blob_sas_url(blob2, self.args_output.sas_duration),
                                       True)
        output_dic = dict()
        self.add_key_value(output_dic, "ACCOUNT",
                           self.args_output.output_storage_account_name, False)

        self.add_key_value(output_dic, "OVERWRITE",
                           str(self.args_output.output_overwrite).lower(), False)

        if "?" in self.datatransfer.output_container:
            # SAS token has been included in container
            container_name_parts = self.datatransfer.output_container.split("?")  
            self.add_key_value(output_dic, "CONTAINER",
                               container_name_parts[0], False)
            self.add_key_value(output_dic, "CONTAINER_SAS",
                               container_name_parts[1], False)
        else:
            self.add_key_value(output_dic, "CONTAINER",
                               self.datatransfer.output_container, False)
            self.add_key_value(output_dic, "CONTAINER_SAS",
                               self.datatransfer.create_output_sas(self.args_output.sas_duration), False)
        self.add_key_value(output_dic, "OUTPUT_FILENAME_BASE",
                           self.args_output.output_filename_base, False)
        self.add_key_value(output_dic, "OUTPUT_INCLUDE_LOGFILES",
                           self.args_output.output_include_logfiles, False)

        return input_dic, output_dic
    def set_exit_code(self, result=None, response_code=None, workflow_status=None):
        """
        Sets exit code from the result, response code and/or workflow status.
        """
        #result always takes priority over the other params.
        if result is not None:
            self.current_exit_status = self.exit_status_by_result[result][1]
            return

        #failure for all edge conditions
        self.current_exit_status = 1000

        #only response code was provided
        if response_code in self.exit_status_by_response and workflow_status is None:
            self.current_exit_status = self.exit_status_by_response[response_code][1]
            return

        #failure in response takes priority when non-success
        if response_code != 200 and response_code in self.exit_status_by_response:
            self.current_exit_status = self.exit_status_by_response[response_code][1]
            return

        if workflow_status in self.exit_status_by_workflow_status:
            self.current_exit_status = self.exit_status_by_workflow_status[workflow_status][1]

    @classmethod
    def add_key_value(cls, dictionary, key, value, append_value):
        """adds a new value pair to the dictionary or appends to an existing value"""
        if append_value:
            if key in dictionary:
                dictionary[key] += value + ","
            else:
                dictionary[key] = value + ","
        else:
            dictionary[key] = value

    @classmethod
    def get_str_value(cls, dictionary, key, default=""):
        """gets a value from a dictionary if the key exists"""
        if not isinstance(dictionary, dict):
            return default
        if key in dictionary:
            value = dictionary[key]
            if value is not None:
                return str(value)
        return default
    