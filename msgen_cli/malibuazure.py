# ----------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License. See LICENSE.rst in the
#  project root for license information. If LICENSE.rst
#  is missing, see https://opensource.org/licenses/MIT
# ----------------------------------------------------------

"""File for all Azure-related functionality"""
import sys
from datetime import datetime, timedelta

from time import sleep
try:
    from azure.storage.blob import BlockBlobService, ContainerPermissions, BlobPermissions
except ImportError:
    print ("You need to install"
           " the 'Microsoft Azure Storage SDK for Python' library."
           " Try: pip install azure-storage")
    sys.exit(1)

def delete_container(
        azure_storage_account_name,
        azure_storage_account_key,
        container_name):
    """Deletes container from the storage account"""
    blob_service = BlockBlobService(account_name=azure_storage_account_name,
                                    account_key=azure_storage_account_key)
    if blob_service.exists(container_name):
        blob_service.delete_container(container_name)
def container_exists(
        azure_storage_account_name,
        azure_storage_account_key,
        container_name):
    """Checks if the container exists in the storage account"""
    blob_service = BlockBlobService(account_name=azure_storage_account_name,
                                    account_key=azure_storage_account_key)
    return blob_service.exists(container_name)

def get_blob_list_in_container(
        azure_storage_account_name,
        azure_storage_account_key,
        container_name,
        num_results):
    """Returns the top n blobs in the container"""
    blob_service = BlockBlobService(account_name=azure_storage_account_name,
                                    account_key=azure_storage_account_key)
    blob_list = blob_service.list_blobs(container_name,
                                        None,
                                        num_results,
                                        None,
                                        "|")
    return blob_list

def create_blob_sas_token(
        azure_storage_account_name,
        azure_storage_account_key,
        container_name,
        blob_name,
        sas_token_hours):
    """Creates a read only sas token to a blob"""
    max_retries = 3
    retry_count = 0
    while True:
        try:
            service = BlockBlobService(
                account_name=azure_storage_account_name,
                account_key=azure_storage_account_key)
            today = datetime.utcnow()
            expiration_date = today + timedelta(hours=sas_token_hours)
            expiration_replaced_date = expiration_date.replace(microsecond=0)
            expiration_date_iso = expiration_replaced_date.isoformat() + "Z"

            # Read access only to this particular blob
            sas_token = service.generate_blob_shared_access_signature(
                container_name,
                blob_name,
                BlobPermissions.READ,
                expiration_date_iso,
            )

            return sas_token
        except Exception as exc:
            retry_count += 1
            if retry_count > max_retries:
                print "Azure storage error: " + str(exc)
                sys.exit(200)
            message = str(exc)
            print message
            sleep(1)

def create_container_sas_token(
        azure_storage_account_name,
        azure_storage_account_key,
        container_name,
        sas_token_hours,
        write_access=False,
        list_access=True):
    """ Creates an Azure SAS token from the given name + key """
    max_retries = 3
    retry_count = 0
    while True:
        try:
            service = BlockBlobService(
                account_name=azure_storage_account_name,
                account_key=azure_storage_account_key)
            if write_access:
                service.create_container(container_name)
            today = datetime.utcnow()
            expiration_date = today + timedelta(hours=sas_token_hours)
            expiration_replaced_date = expiration_date.replace(microsecond=0)
            expiration_date_iso = expiration_replaced_date.isoformat() + "Z"
            service.create_container(container_name=container_name)
            permissions = ContainerPermissions(read=True,
                                               list=list_access,
                                               delete=write_access,
                                               write=write_access)

            sas_token = service.generate_container_shared_access_signature(
                container_name=container_name,
                expiry=expiration_date_iso,
                permission=permissions)
            return sas_token
        except Exception as exc:
            retry_count += 1
            if retry_count > max_retries:
                print "Azure storage error: " + str(exc)
                sys.exit(200)
            message = str(exc)
            print message
            sleep(1)
