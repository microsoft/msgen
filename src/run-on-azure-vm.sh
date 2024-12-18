#!/bin/bash
# 12/17/2024 - this is still experimental
set -e

AZURE_LOCATION="westus"
STEM_NAME="msgen243"
IDENTITY_RESOURCE_GROUP="${STEM_NAME}-identity-rg"
RESOURCE_GROUP="${STEM_NAME}-rg"
IDENTITY_NAME="${STEM_NAME}-identity"
VM_NAME="${STEM_NAME}-vm"
VM_SIZE="Standard_D64d_v5"
ADMIN_USERNAME="azureuser"
PASSWORD=$(< /dev/urandom tr -dc 'A-Za-z0-9' | head -c 16)

SCRIPT_URL="https://raw.githubusercontent.com/microsoft/msgen/refs/heads/main/src/msgen.ps1"
INPUT_URL1="https://datasetmsgen.blob.core.windows.net/testinputs/input1.fq.gz"
INPUT_URL2="https://datasetmsgen.blob.core.windows.net/testinputs/input2.fq.gz"
OUTPUT_URL_PREFIX="https://datasetmsgen.blob.core.windows.net/testoutputs"

cleanup() {
  read -p "Do you want to delete the resource group '$RESOURCE_GROUP'? (y/n): " CONFIRM
  if [[ "$CONFIRM" == "y" ]]; then
    echo "Deleting resource group $RESOURCE_GROUP..."
    az group delete --name "$RESOURCE_GROUP" --yes --no-wait || true
  fi
}
trap cleanup ERR

fetch_boot_log() {
  echo "Fetching boot diagnostics log for VM $VM_NAME..."
  BOOT_LOG=$(az vm boot-diagnostics get-boot-log --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" -o tsv 2>/dev/null)
  if [[ -n "$BOOT_LOG" ]]; then
    echo "=== Boot Diagnostics Log ==="
    echo "$BOOT_LOG"
  else
    echo "No boot diagnostics log available."
  fi
}

trap 'fetch_boot_log; exit 1' ERR

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

IDENTITY_ID=$(az identity show --name "$IDENTITY_NAME" --resource-group "$IDENTITY_RESOURCE_GROUP" --query id -o tsv)

echo "Fetching the latest image for MicrosoftWindowsServer:WindowsServer:2022-datacenter-azure-edition..."
LATEST_IMAGE=$(az vm image list \
  --publisher MicrosoftWindowsServer \
  --offer WindowsServer \
  --sku 2022-datacenter-azure-edition \
  --architecture x64 \
  --all \
  --query "[?offer=='WindowsServer' && sku=='2022-datacenter-azure-edition'].{Version: version, URN: urn} | sort_by(@, &Version)[-1].URN" -o tsv)
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

# Enable boot diagnostics for real-time log retrieval
echo "Enabling boot diagnostics for the virtual machine..."
az vm boot-diagnostics enable --name "$VM_NAME" --resource-group "$RESOURCE_GROUP"

VM_ID=$(az vm show --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
echo "Assigning managed identity $IDENTITY_NAME to virtual machine $VM_NAME..."
az vm identity assign --identities "$IDENTITY_ID" --ids "$VM_ID"

COMMAND_TO_EXECUTE="powershell -ExecutionPolicy Unrestricted -File msgen.ps1 -inputUrl1 $INPUT_URL1"
if [[ -n "$INPUT_URL2" ]]; then
  COMMAND_TO_EXECUTE+=" -inputUrl2 $INPUT_URL2"
fi
COMMAND_TO_EXECUTE+=" -outputUrlPrefix $OUTPUT_URL_PREFIX"

echo "Adding Custom Script Extension to run PowerShell script on VM..."
az vm extension set \
  --resource-group "$RESOURCE_GROUP" \
  --vm-name "$VM_NAME" \
  --name "CustomScriptExtension" \
  --publisher "Microsoft.Compute" \
  --settings "{\"fileUris\": [\"$SCRIPT_URL\"], \"commandToExecute\": \"$COMMAND_TO_EXECUTE\"}"

# Poll for Custom Script Extension execution
echo "Waiting for Custom Script Extension execution to complete..."

EXTENSION_LOG_FILE="/tmp/vm-extension-log.txt"
while true; do
  EXT_STATUS=$(az vm extension show \
    --resource-group "$RESOURCE_GROUP" \
    --vm-name "$VM_NAME" \
    --name "CustomScriptExtension" \
    --query 'instanceView.statuses[?code].message' -o tsv 2>/dev/null)

  if [[ "$EXT_STATUS" == *"Provisioning succeeded"* ]]; then
    echo "Custom Script Extension completed successfully."
    break
  elif [[ "$EXT_STATUS" == *"Provisioning failed"* ]]; then
    echo "Custom Script Extension failed. Fetching boot diagnostics log..."
    fetch_boot_log
    exit 1
  else
    echo "Custom Script Extension still running... Checking status again..."
  fi
  sleep 10
done
