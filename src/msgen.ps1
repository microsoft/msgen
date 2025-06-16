param (
    [string]$inputUrl1,
    [string]$inputUrl2 = $null,
    [string]$outputUrlPrefix,
    [string]$identityResourceId,

     # Optional parameters
    [string]$msgenDownloadUrl = "https://datasetmsgen.blob.core.windows.net/dataset/msgen-oss/msgen-oss.zip",

     # Optional parameters for deleting the VM's resource group on completion
    [string]$subscriptionId = $null,
    [string]$resourceGroupName = $null,
    [string]$vmName = $null
)

$ErrorActionPreference = "Stop"

$azCopyDownloadUrl = "https://aka.ms/downloadazcopy-v10-windows"
$azCopyInstallDir = "C:\azcopy" 
$tempDir = $env:TEMP
$hg38m1xUrl = "https://datasetmsgen.blob.core.windows.net/dataset/hg38m1x/*"
$hg38m1xIdxUrl = "https://datasetmsgen.blob.core.windows.net/dataset/hg38m1x.idx/*"
$logsZipPath = "$tempDir\logs\logs.zip"
$dotnetRuntimeUrl = "https://builds.dotnet.microsoft.com/dotnet/Runtime/9.0.6/dotnet-runtime-9.0.6-win-x64.exe"
$dotnetRuntimeInstallerPath = "$tempDir\dotnet-runtime-9.0.6-win-x64.exe"
$javaInstallerBinaryName = "zulu8.36.0.25-ca-jdk8.0.452-win_x64.msi"
$javaInstallerPath = "$tempDir\$javaInstallerBinaryName"
$javaDownloadUrl = "https://cdn.azul.com/zulu/bin/zulu8.84.0.15-ca-jdk8.0.442-win_x64.msi"
$defaultJavaPath = "C:\java\bin\java.exe"

# Function to check if .NET 9 Runtime is installed
function Is-DotNet9Installed {
    $runtimes = & dotnet --list-runtimes 2>$null
    return $runtimes -match "9\."
}

try {
    # Create directories if they don't exist
    if (-not (Test-Path -Path $azCopyInstallDir)) {
        New-Item -Path $azCopyInstallDir -ItemType Directory | Out-Null
        Write-Host "Created directory: $azCopyInstallDir"
    } else {
        Write-Host "Directory already exists: $azCopyInstallDir"
    }

    if (-not (Test-Path -Path $tempDir)) {
        New-Item -Path $tempDir -ItemType Directory | Out-Null
        Write-Host "Created directory: $tempDir"
    } else {
        Write-Host "Directory already exists: $tempDir"
    }

    # Download and unzip AzCopy
    Write-Host "Downloading AzCopy..."
    $webClient = New-Object Net.WebClient
    $azCopyZipPath = "$env:TEMP\azcopy.zip"
    $webClient.DownloadFile($azCopyDownloadUrl, $azCopyZipPath)
    Expand-Archive -Path "$env:TEMP\azcopy.zip" -DestinationPath $azCopyInstallDir -Force
    $azCopyExe = (Get-ChildItem -Path $azCopyInstallDir -Recurse -Filter "azcopy.exe" | Select-Object -First 1).FullName
    Move-Item -Path $azCopyExe -Destination "$azCopyInstallDir\azcopy.exe"

    # Create necessary directories
    Write-Host "Creating directories..."
    New-Item -ItemType Directory -Path "$tempDir\resources\references" -Force | Out-Null
    New-Item -ItemType Directory -Path "$tempDir\outputs" -Force | Out-Null
    New-Item -ItemType Directory -Path "$tempDir\logs" -Force | Out-Null
    New-Item -ItemType Directory -Path "$tempDir\inputs" -Force | Out-Null

    # Download reference files
    Write-Host "Downloading reference files..."
    & "$azCopyInstallDir\azcopy.exe" cp $hg38m1xUrl "$tempDir\resources\references\hg38m1x" --overwrite=false --recursive
    & "$azCopyInstallDir\azcopy.exe" cp $hg38m1xIdxUrl "$tempDir\resources\references\hg38m1x.idx" --overwrite=false --recursive


    # Download input files
    Write-Host "Authenticating AZCOPY with the user-assigned managed identity..."
    & "$azCopyInstallDir\azcopy.exe" login --identity --identity-resource-id $identityResourceId
    

    Write-Host "Downloading input files..."
    & "$azCopyInstallDir\azcopy.exe" cp $inputUrl1 "$tempDir\inputs"
    if (![string]::IsNullOrEmpty($inputUrl2)) {
        & "$azCopyInstallDir\azcopy.exe" cp $inputUrl2 "$tempDir\inputs"
    }

    if (!(Test-Path $defaultJavaPath)) {
        Write-Host "Java not found, downloading installer..."
        (New-Object Net.WebClient).DownloadFile($javaDownloadUrl, $javaInstallerPath)
        Write-Host "Installing Java..."
        Start-Process -FilePath "msiexec.exe" -ArgumentList "/quiet /i `"$javaInstallerPath`" INSTALLDIR=C:\java\" -Wait
        if ($LASTEXITCODE -ne 0) { throw "Java installation failed. Exit code: $LASTEXITCODE" }
        Write-Host "Java installed successfully."
    } else {
        Write-Host "Java is already installed."
    }


    # Download and unzip msgen-oss
    Write-Host "Downloading msgen-oss..."
    & "$azCopyInstallDir\azcopy.exe" cp $msgenDownloadUrl "$tempDir" --recursive
    Expand-Archive -Path "$tempDir\msgen-oss.zip" -DestinationPath "$tempDir\msgen" -Force

    # Download needed dotnet version
    if (Is-DotNet9Installed) {
        Write-Host ".NET 9 runtime is already installed." -ForegroundColor Green
    } else {
        Write-Host ".NET 9 runtime not found. Installing..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $dotnetRuntimeUrl -OutFile $dotnetRuntimeInstallerPath

        # Install silently (no UI)
        Start-Process -FilePath $dotnetRuntimeInstallerPath -ArgumentList "/install", "/quiet", "/norestart" -Wait

        # Clean up
        Remove-Item $dotnetRuntimeInstallerPath
        
        # Confirm installation
        if (Is-DotNet9Installed) {
            Write-Host ".NET 9 runtime was successfully installed." -ForegroundColor Green
        } else {
            Write-Host "Installation failed or .NET 9 runtime not detected." -ForegroundColor Red
        }
    }

    # Run msgen-oss
    Write-Host "Running msgen-oss..."
    & "$tempDir\msgen\msgen-oss.exe" $tempDir "$tempDir\inputs" "$tempDir\outputs" "$tempDir\logs" "$tempDir\resources" "R=hg38m1x;GERC=GVCF;BGZIP=True"

    # Upload outputs
    Write-Host "Uploading outputs..."

    # Check if outputs directory exists and is not empty
    if ((Test-Path -Path "$tempDir\outputs") -and ((Get-ChildItem -Path "$tempDir\outputs" -File | Measure-Object).Count -gt 0)) {
    & "$azCopyInstallDir\azcopy.exe" cp "$tempDir\outputs\*" $outputUrlPrefix --recursive
    } else {
        Write-Host "Skipping outputs upload: Directory does not exist or is empty."
    }

    # Check if logs directory exists and is not empty
    if ((Test-Path -Path "$tempDir\logs") -and ((Get-ChildItem -Path "$tempDir\logs" -File | Measure-Object).Count -gt 0)) {
        # Zip logs directory
        Write-Host "Zipping logs directory..."
        Compress-Archive -Path "$tempDir\logs\*" -DestinationPath $logsZipPath -Force

        # Upload logs.zip
        Write-Host "Uploading logs.zip..."


        & "$azCopyInstallDir\azcopy.exe" cp $logsZipPath $outputUrlPrefix
    } else {
        Write-Host "Skipping logs upload: Directory does not exist or is empty."
    }

    Write-Host "Completed genomics successfully."
    
} catch {
    Write-Host "An error occurred: $($_.Exception.Message)"
    exit 1
}

# Delete VM resouce group if set
if ($subscriptionId -ne $null -and $resourceGroupName -ne $null -and $vmName -ne $null) {
    Write-Host "Deleting this VM now..."

    Write-Host "Installing Azure CLI..."

    # Azure CLI MSI installer URL
    $azureCliInstallerUrl = "https://aka.ms/installazurecliwindows"
    $installerPath = "$env:TEMP\AzureCLIInstaller.msi"

    # Download Azure CLI installer using WebClient
    Write-Host "Downloading Azure CLI installer from $azureCliInstallerUrl..."
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($azureCliInstallerUrl, $installerPath)

    # Install Azure CLI silently
    Write-Host "Installing Azure CLI..."
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/I `"$installerPath`" /quiet /norestart" -Wait

    # Cleanup the installer
    Remove-Item -Path $installerPath -Force
    Write-Host "Azure CLI installed successfully."

    # Add Azure CLI to PATH
    $azPath = "C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin"
    if (-not ($env:PATH -like "*$azPath*")) {
        $env:PATH += ";$azPath"
    }

    # Step 2: Authenticate using User Assigned Managed Identity (UAMI)
    Write-Host "Authenticating using User Assigned Managed Identity..."
    $loginResult = az login --identity --resource-id $identityResourceId --query '[0].id' -o tsv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to authenticate with the User Assigned Managed Identity. Exiting..."
        exit 1
    }
    Write-Host "Authentication successful."

    az account set --subscription $subscriptionId

    Write-Host "Deleting the VM's resource group..."
    az group delete --name $resourceGroupName --yes --no-wait

    Write-Host "VM resource group deletion initiated. Everything complete."
}
