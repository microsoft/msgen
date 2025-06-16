#!/bin/bash
set -e

INPUT_URL1="${1}"
INPUT_URL2="${2}"
OUTPUT_URL_PREFIX="${3}"
AZURE_LOCATION="${4:-westus2}"
STEM_NAME="${5:-msgen2025}"
RESOURCE_GROUP="${6:-${STEM_NAME}-vm}"
IDENTITY_RESOURCE_GROUP="${7:-${STEM_NAME}-identity}"
IDENTITY_NAME="${8:-${STEM_NAME}-identity}"
VM_SIZE="${9:-Standard_D64d_v5}"

VM_NAME="${STEM_NAME}-vm"
ADMIN_USERNAME="azureuser"
PASSWORD="$(< /dev/urandom tr -dc 'A-Za-z0-9' | head -c 16)!"
SCRIPT_URL="https://raw.githubusercontent.com/microsoft/msgen/refs/heads/main/src/msgen.ps1"
MSGEN_BINARIES_URL="https://datasetmsgen.blob.core.windows.net/dataset/msgen-oss/msgen-oss.zip"
SUBSCRIPTION_ID=$(az account show --query id -o tsv | tr -d '\r')

cleanup() {
  read -p "Do you want to delete the resource group '$RESOURCE_GROUP'? (y/n): " CONFIRM
  if [[ "$CONFIRM" == "y" ]]; then
    echo "Deleting resource group $RESOURCE_GROUP..."
    az group delete --name "$RESOURCE_GROUP" --yes --no-wait || true
  fi
}
trap cleanup ERR

# Check if the identity resource group exists
if ! az group exists --name "$IDENTITY_RESOURCE_GROUP" | grep -q "true"; then
  echo "Creating resource group $IDENTITY_RESOURCE_GROUP in $AZURE_LOCATION..."
  az group create --name "$IDENTITY_RESOURCE_GROUP" --location "$AZURE_LOCATION"
else
  echo "Resource group $IDENTITY_RESOURCE_GROUP already exists. Skipping creation."
fi

# Check if the main resource group exists
if ! az group exists --name "$RESOURCE_GROUP" | grep -q "true"; then
  echo "Creating resource group $RESOURCE_GROUP in $AZURE_LOCATION..."
  az group create --name "$RESOURCE_GROUP" --location "$AZURE_LOCATION"
else
  echo "Resource group $RESOURCE_GROUP already exists. Skipping creation."
fi

# Check if the managed identity exists
if ! az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "Creating managed identity $IDENTITY_NAME in resource group $IDENTITY_RESOURCE_GROUP..."
  az identity create --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP"
else
  echo "Managed identity $IDENTITY_NAME already exists. Skipping creation."
fi

IDENTITY_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --query id -o tsv | tr -d '\r')

echo "Assigning Contributor role to the managed identity for the resource group $RESOURCE_GROUP..."
IDENTITY_OBJECT_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --query principalId -o tsv | tr -d '\r')

# Assign the Contributor role using the object ID and specifying the principal type
az role assignment create \
  --assignee-object-id "$IDENTITY_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

echo "Fetching the latest image for MicrosoftWindowsServer:WindowsServer:2022-datacenter-azure-edition..."
LATEST_IMAGE=$(az vm image list \
  --publisher MicrosoftWindowsServer \
  --offer WindowsServer \
  --sku 2022-datacenter-azure-edition \
  --architecture x64 \
  --all \
  --query "[?offer=='WindowsServer' && sku=='2022-datacenter-azure-edition'].{Version: version, URN: urn} | sort_by(@, &Version)[-1].URN" -o tsv | tr -d '\r')
echo "Selected image: $LATEST_IMAGE"

echo "Creating virtual machine $VM_NAME in resource group $RESOURCE_GROUP..."
az vm create \
  --name "$VM_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --size "$VM_SIZE" \
  --image "$LATEST_IMAGE" \
  --admin-username "$ADMIN_USERNAME" \
  --admin-password "$PASSWORD" \
  --enable-secure-boot \
  --enable-vtpm


VM_ID=$(az vm show --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv | tr -d '\r')
echo "Assigning managed identity $IDENTITY_NAME to virtual machine $VM_NAME..."
az vm identity assign --identities "$IDENTITY_ID" --ids "$VM_ID"

# Uncomment to access RDP:
#echo "Opening port 3389 for virtual machine $VM_NAME..."
#az vm open-port --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" --port 3389
#IP=$(az vm show --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" --show-details --query publicIps -o tsv)
#echo "Remote Desktop Connection Details:"
#echo "IP Address: $IP"
#echo "Username: $ADMIN_USERNAME"
#echo "Password: $PASSWORD"

COMMAND_TO_EXECUTE="powershell -ExecutionPolicy Unrestricted -File msgen.ps1 -inputUrl1 $INPUT_URL1"
if [[ -n "$INPUT_URL2" ]]; then
  COMMAND_TO_EXECUTE+=" -inputUrl2 $INPUT_URL2"
fi
COMMAND_TO_EXECUTE+=" -outputUrlPrefix $OUTPUT_URL_PREFIX"
COMMAND_TO_EXECUTE+=" -identityResourceId $IDENTITY_ID"
COMMAND_TO_EXECUTE+=" -msgenDownloadUrl $MSGEN_BINARIES_URL"
COMMAND_TO_EXECUTE+=" -subscriptionId $SUBSCRIPTION_ID"
COMMAND_TO_EXECUTE+=" -resourceGroupName $RESOURCE_GROUP"
COMMAND_TO_EXECUTE+=" -vmName $VM_NAME"

echo "Command to execute: $COMMAND_TO_EXECUTE"

echo "Note: '(OperationPreempted)' is expected when the VM resource group deletes itself."
echo "Running PowerShell script on VM..."
az vm extension set \
  --resource-group "$RESOURCE_GROUP" \
  --vm-name "$VM_NAME" \
  --name "CustomScriptExtension" \
  --publisher "Microsoft.Compute" \
  --settings "{\"fileUris\": [\"$SCRIPT_URL\"], \"commandToExecute\": \"$COMMAND_TO_EXECUTE\"}"

# Note: add "--no-wait" to the previous command to avoid waiting for the script to complete

echo "Done. VM is now running and will delete itself upon completion."

