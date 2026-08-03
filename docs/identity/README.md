# ProofGrid identity proof

These screenshots freeze the structural direction before product
implementation. They are generated from `identity-preview.html`, which depicts
the defining working state rather than a marketing cover.

Render on Windows with Chrome installed:

```powershell
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$htmlPath = (Resolve-Path 'docs\identity\identity-preview.html').Path
$url = 'file:///' + ($htmlPath -replace '\\','/')
$out = (Resolve-Path 'docs\identity').Path
& $chrome --headless --disable-gpu --hide-scrollbars --window-size=1440,1000 --screenshot="$out\proofgrid-1440.png" $url
& $chrome --headless --disable-gpu --hide-scrollbars --window-size=1024,900 --screenshot="$out\proofgrid-1024.png" $url
& $chrome --headless --disable-gpu --hide-scrollbars --window-size=390,844 --screenshot="$out\proofgrid-390.png" $url
```

Manual review on 2026-08-01: `PASS` at all three widths. The mobile proof uses
a pinned case axis and horizontal run comparison by design; the page chrome and
evidence tray themselves do not require horizontal scrolling.
