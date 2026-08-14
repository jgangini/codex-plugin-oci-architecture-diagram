$ErrorActionPreference = 'Stop'

if (Test-Path -LiteralPath 'graphify-out\GRAPH_REPORT.md') {
    graphify update .
}

if (Test-Path -LiteralPath '.sentrux\rules.toml') {
    sentrux check .
    sentrux gate .
}
