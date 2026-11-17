$ErrorActionPreference = 'Stop'

if (Test-Path -LiteralPath 'graphify-out\GRAPH_REPORT.md') {
    Get-Content -LiteralPath 'graphify-out\GRAPH_REPORT.md' -TotalCount 120
}

if (Test-Path -LiteralPath '.sentrux\rules.toml') {
    sentrux gate --save .
    sentrux check .
}
