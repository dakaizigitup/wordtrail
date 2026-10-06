param([string]$SettingsPath = (Join-Path $env:APPDATA 'Qingjian\wordtrail-vocabulary.json'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$qjIds = @('cet4','cet6','tem4','tem8','toefl','ielts')
$qjNames = @('四级','六级','专四','专八','托福','雅思')
$qjSelected = @()
if(Test-Path -LiteralPath $SettingsPath){
    try{$qjSelected = @((Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json).targets)}
    catch{[System.Windows.Forms.MessageBox]::Show('原目标文件无法读取。保存后将使用本次选择。','词伴')|Out-Null}
}
$qjForm = [System.Windows.Forms.Form]::new()
$qjForm.Text = '词伴 · 英语学习目标'
$qjForm.ClientSize = [System.Drawing.Size]::new(520,330)
$qjForm.Font = [System.Drawing.Font]::new('Microsoft YaHei UI',10)
$qjForm.StartPosition = 'CenterScreen'
$qjForm.FormBorderStyle = 'FixedDialog'
$qjForm.MaximizeBox = $false
$qjForm.BackColor = [System.Drawing.Color]::FromArgb(244,248,245)
$qjHint = [System.Windows.Forms.Label]::new()
$qjHint.Text = "可多选，命中任一目标的英文译词优先。`r`n中文候选顺序不变，未命中译词仍保留。"
$qjHint.SetBounds(24,20,472,55)
$qjForm.Controls.Add($qjHint)
$qjBoxes = @()
for($qjIndex=0;$qjIndex -lt 6;$qjIndex++){
    $qjCheck = [System.Windows.Forms.CheckBox]::new()
    $qjCheck.Text = $qjNames[$qjIndex]
    $qjCheck.Checked = $qjSelected -contains $qjIds[$qjIndex]
    $qjCheck.SetBounds((24+($qjIndex%3)*160),(86+[Math]::Floor($qjIndex/3)*44),148,36)
    $qjForm.Controls.Add($qjCheck)
    $qjBoxes += $qjCheck
}
$qjNote = [System.Windows.Forms.Label]::new()
$qjNote.Text = "不选目标 = 全部词汇、原译词顺序。`r`n同词可有多个标签，标签表示社区词表收录类别，`r`n不是难度等级或官方完整考试范围。保存后约一秒生效。"
$qjNote.SetBounds(24,180,472,74)
$qjForm.Controls.Add($qjNote)
$qjAll = [System.Windows.Forms.Button]::new()
$qjAll.Text = '全部词汇 / 清除目标'
$qjAll.SetBounds(24,272,220,38)
$qjAll.Add_Click({foreach($qjBox in $qjBoxes){$qjBox.Checked=$false}})
$qjForm.Controls.Add($qjAll)
$qjSave = [System.Windows.Forms.Button]::new()
$qjSave.Text = '保存'
$qjSave.SetBounds(346,272,150,38)
$qjSave.Add_Click({
    try {
        $qjTargets=@(for($qjN=0;$qjN -lt 6;$qjN++){if($qjBoxes[$qjN].Checked){$qjIds[$qjN]}})
        $qjFolder = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($SettingsPath))
        [System.IO.Directory]::CreateDirectory($qjFolder)|Out-Null
        $qjTemporary = Join-Path $qjFolder ([System.IO.Path]::GetRandomFileName())
        [System.IO.File]::WriteAllText($qjTemporary,(@{targets=$qjTargets}|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
        if(Test-Path -LiteralPath $SettingsPath){[System.IO.File]::Replace($qjTemporary,$SettingsPath,$null)}
        else{[System.IO.File]::Move($qjTemporary,$SettingsPath)}
        $qjForm.Close()
    } catch {[System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'保存失败')|Out-Null}
})
$qjForm.Controls.Add($qjSave)
$qjForm.AcceptButton = $qjSave
[void]$qjForm.ShowDialog()
