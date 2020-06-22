# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""Data transfer functionality"""
import malibuazure

class AzureDataTransfer(object):

    """ Main class for working with workflows """
    def __init__(self, storage_account_info):
        """ Constructor """
        self.storage_info = storage_account_info
        self.input_container = self.storage_info.input.container
        self.output_container = self.storage_info.output.container

    def create_input_blob_sas_url(self, blob_name, sas_token_hours):
        """creates a sas token for the blob name"""
        if blob_name is None or blob_name == "":
            return ""

        sas_token = malibuazure.create_blob_sas_token(
            self.storage_info.input.name,
            self.storage_info.input.key,
            self.input_container,
            blob_name,
            sas_token_hours)

        return blob_name + '?' + sas_token

    def create_output_sas(self, sas_token_hours):
        """ Creates a container sas token in the output storage account """
        sas_token = malibuazure.create_container_sas_token(
            self.storage_info.output.name,
            self.storage_info.output.key,
            self.output_container,
            sas_token_hours,
            True,
            False)

        return sas_token
