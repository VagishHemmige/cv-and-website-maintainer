param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Destination
)
$ErrorActionPreference = 'Stop'
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $destinationPath) { throw 'Destination already exists' }
if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($destinationPath)))) { throw 'Missing output directory' }
if ([IO.Path]::GetExtension($sourcePath).ToLowerInvariant() -notin @('.ppt','.pptx')) { throw 'Expected PPT/PPTX' }
$existingPowerPoint = @(Get-Process -Name POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$application = $null
$deck = $null
try {
    $application = New-Object -ComObject PowerPoint.Application
    $application.AutomationSecurity = 3 # Disable macros for programmatic open.
    $deck = $application.Presentations.Open($sourcePath, -1, -1, 0)
    $deck.SaveAs($destinationPath, 32) # ppSaveAsPDF; source opened read-only/untitled.
    if (-not (Test-Path -LiteralPath $destinationPath)) { throw 'No PDF was exported' }
} finally {
    if ($null -ne $deck) {
        $deck.Close()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($deck)
    }
    if ($null -ne $application) {
        if (-not $existingPowerPoint) { $application.Quit() }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($application)
    }
}
