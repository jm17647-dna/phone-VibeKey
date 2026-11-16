# 以管理员身份运行：为当前 Python 放行局域网入站（仅专用网络）
$ErrorActionPreference = 'Stop'
$exe = (Get-Command python).Source
netsh advfirewall firewall delete rule name="VoiceBridge" | Out-Null
netsh advfirewall firewall add rule name="VoiceBridge" dir=in action=allow program="$exe" profile=private,domain,public enable=yes
netsh advfirewall firewall delete rule name="VoiceBridge-8765" | Out-Null
Write-Host "完成：已按程序放行 $exe（专用/域/公用网络）"
