param(
    [Parameter(Mandatory = $true)]
    [string]$TextFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputWav
)

$ErrorActionPreference = "Stop"

try {
    Add-Type -AssemblyName System.Speech

    $text = Get-Content -LiteralPath $TextFile -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "The narration script is empty."
    }

    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer

    try {
        # Use the default voice installed on this Windows system.
        $synth.SetOutputToWaveFile($OutputWav)
        $synth.Speak($text)
        $synth.SetOutputToNull()
    }
    finally {
        $synth.Dispose()
    }

    if (!(Test-Path -LiteralPath $OutputWav)) {
        throw "The speech engine did not create the WAV output."
    }

    if ((Get-Item -LiteralPath $OutputWav).Length -eq 0) {
        throw "The generated WAV file is empty."
    }

    Write-Output "Narration created successfully."
    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
