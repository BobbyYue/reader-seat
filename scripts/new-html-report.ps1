param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Name,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$BaseDir,

    [switch]$Charts,
    [switch]$Diagrams
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$BaseDir = [System.IO.Path]::GetFullPath($BaseDir)
$OutDir = Join-Path $BaseDir $Name

if (Test-Path $OutDir) {
    throw "Output directory already exists: $OutDir"
}

New-Item -ItemType Directory -Path (Join-Path $OutDir "assets") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $OutDir "_shared/fonts") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $OutDir "_shared/js") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $OutDir "_shared/licenses") -Force | Out-Null

$FontDir = Join-Path $SkillDir "assets/html/fonts"
Copy-Item (Join-Path $FontDir "WorkSans-Regular.ttf") (Join-Path $OutDir "_shared/fonts/")
Copy-Item (Join-Path $FontDir "WorkSans-Bold.ttf") (Join-Path $OutDir "_shared/fonts/")
Copy-Item (Join-Path $FontDir "RedHatMono-Regular.ttf") (Join-Path $OutDir "_shared/fonts/")
Copy-Item (Join-Path $FontDir "RedHatMono-Bold.ttf") (Join-Path $OutDir "_shared/fonts/")
Copy-Item (Join-Path $SkillDir "assets/html/THIRD_PARTY_NOTICES.md") (Join-Path $OutDir "_shared/licenses/")
Copy-Item (Join-Path $FontDir "WorkSans-OFL.txt") (Join-Path $OutDir "_shared/licenses/")
Copy-Item (Join-Path $FontDir "RedHatMono-OFL.txt") (Join-Path $OutDir "_shared/licenses/")

if ($Charts) {
    Copy-Item (Join-Path $SkillDir "assets/html/js/echarts.min.js") (Join-Path $OutDir "_shared/js/")
}
if ($Diagrams) {
    Copy-Item (Join-Path $SkillDir "assets/html/js/mermaid.min.js") (Join-Path $OutDir "_shared/js/")
}

$TemplatePath = Join-Path $SkillDir "assets/html/report-template.html"
$HtmlPath = Join-Path $OutDir "$Name.html"
Copy-Item $TemplatePath $HtmlPath

Write-Host "Created: $HtmlPath"
Write-Host "Created: $(Join-Path $OutDir 'assets/')"
Write-Host "Copied: bundled Reader's Seat fonts"
Write-Host "Copied: third-party notices"
if ($Charts) { Write-Host "Copied: ECharts" }
if ($Diagrams) { Write-Host "Copied: Mermaid" }
