# Copy and Paste this into Powershell on windows to set up the path for the postgres bin directory

# Detect PostgreSQL installation directory
$possibleRoots = @(
    "${env:ProgramFiles}\PostgreSQL",
    "${env:ProgramFiles(x86)}\PostgreSQL"
)

$pgBin = $null

foreach ($root in $possibleRoots) {
    if (Test-Path $root) {
        $versions = Get-ChildItem $root -Directory | Sort-Object Name -Descending
        foreach ($ver in $versions) {
            $candidate = Join-Path $ver.FullName "bin"
            if (Test-Path (Join-Path $candidate "createuser.exe")) {
                $pgBin = $candidate
                break
            }
        }
    }
    if ($pgBin) { break }
}

if ($pgBin) {
    if ($env:PATH -notlike "*$pgBin*") {
        [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$pgBin", [EnvironmentVariableTarget]::User)
        $env:PATH += ";$pgBin"
        Write-Host "✅ PostgreSQL bin directory added to PATH: $pgBin"
    } else {
        Write-Host "ℹ️ PostgreSQL bin directory already in PATH: $pgBin"
    }
} else {
    Write-Warning "❌ Could not find PostgreSQL installation with 'createuser.exe'. Please install PostgreSQL and rerun."
}
