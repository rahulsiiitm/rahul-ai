param(
    [string]$PortfolioRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) "..\portfolio"),
    [switch]$Check
)

$backendData = Join-Path (Split-Path $PSScriptRoot -Parent) "zero-backend\data"
$portfolioData = Join-Path $PortfolioRoot "data"
$sharedFiles = @("projects.json", "experience.json", "achievements.json")
$different = @()

foreach ($name in $sharedFiles) {
    $source = Join-Path $portfolioData $name
    $destination = Join-Path $backendData $name
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing canonical portfolio data file: $source"
    }

    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
    $destinationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash
    if ($sourceHash -ne $destinationHash) {
        $different += $name
        if (-not $Check) {
            Copy-Item -LiteralPath $source -Destination $destination -Force
        }
    }
}

if ($Check -and $different.Count -gt 0) {
    throw "Backend portfolio data is out of sync: $($different -join ', ')"
}

if ($different.Count -eq 0) {
    Write-Output "Portfolio data is already synchronized."
} elseif (-not $Check) {
    Write-Output "Synchronized: $($different -join ', ')"
}
