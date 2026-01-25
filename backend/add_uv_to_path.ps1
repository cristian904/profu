# Script to add uv to PATH permanently
$uvPath = "$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Python310\Scripts"

# Check if uv.exe exists
if (Test-Path "$uvPath\uv.exe") {
    # Get current user PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    # Check if already in PATH
    if ($currentPath -notlike "*$uvPath*") {
        # Add to PATH
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$uvPath", "User")
        Write-Host "✓ Added uv to PATH: $uvPath" -ForegroundColor Green
        Write-Host "Please restart your terminal for changes to take effect." -ForegroundColor Yellow
    } else {
        Write-Host "✓ uv is already in PATH" -ForegroundColor Green
    }
    
    # Also add to current session
    $env:Path += ";$uvPath"
    Write-Host "✓ Added to current session. You can now use 'uv' in this terminal." -ForegroundColor Green
    
    # Verify
    Write-Host "`nVerifying installation..." -ForegroundColor Cyan
    & "$uvPath\uv.exe" --version
} else {
    Write-Host "✗ uv.exe not found at: $uvPath" -ForegroundColor Red
    Write-Host "Please install uv first: pip install uv" -ForegroundColor Yellow
}
