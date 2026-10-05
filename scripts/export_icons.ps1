# Mechanical platform-size exports of the generated master artwork; no content changes.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$iconRoot=Split-Path $PSScriptRoot -Parent
$iconMaster=[System.Drawing.Image]::FromFile((Join-Path $iconRoot 'branding/wordtrail-warm-master.png'))
function Export-WordtrailIcon([string]$Relative,[int]$Size) {
    $iconTarget=Join-Path $iconRoot $Relative
    New-Item -ItemType Directory -Path (Split-Path $iconTarget -Parent) -Force | Out-Null
    # App Store icons require RGB with no alpha channel, even for opaque pixels.
    $iconBitmap=New-Object System.Drawing.Bitmap($Size,$Size,[System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $iconCanvas=[System.Drawing.Graphics]::FromImage($iconBitmap)
    try {
        $iconCanvas.Clear([System.Drawing.Color]::FromArgb(255,255,249,234))
        $iconCanvas.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $iconCanvas.PixelOffsetMode=[System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $iconCanvas.DrawImage($iconMaster,0,0,$Size,$Size)
        $iconBitmap.Save($iconTarget,[System.Drawing.Imaging.ImageFormat]::Png)
    } finally {$iconCanvas.Dispose();$iconBitmap.Dispose()}
}
try {
    Export-WordtrailIcon 'branding/wordtrail-warm-icon.png' 1024
    Export-WordtrailIcon 'android/app/src/main/res/drawable-nodpi/wordtrail_mark.png' 256
    Export-WordtrailIcon 'android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png' 192
    Export-WordtrailIcon 'android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png' 144
    Export-WordtrailIcon 'android/app/src/main/res/mipmap-xhdpi/ic_launcher.png' 96
    Export-WordtrailIcon 'android/app/src/main/res/mipmap-hdpi/ic_launcher.png' 72
    Export-WordtrailIcon 'android/app/src/main/res/mipmap-mdpi/ic_launcher.png' 48
    Export-WordtrailIcon 'ios/App/Assets.xcassets/AppIcon.appiconset/AppIcon.png' 1024
    Export-WordtrailIcon 'ios/App/Assets.xcassets/WordtrailMark.imageset/WordtrailMark.png' 144
} finally {$iconMaster.Dispose()}
