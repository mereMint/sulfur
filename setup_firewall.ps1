# Dieses Skript konfiguriert die Windows Defender Firewall, um eingehenden Datenverkehr
# für das Sulfur Bot Web Dashboard auf Port 5000 zu ermöglichen.
#
# WICHTIG: Dieses Skript muss EINMALIG als Administrator ausgeführt werden.
# 1. Rechtsklicke auf das Startmenü und wähle "Terminal (Administrator)" oder "PowerShell (Administrator)".
# 2. Navigiere zu deinem Bot-Verzeichnis: cd c:\sulfur
# 3. Führe dieses Skript aus: .\setup_firewall.ps1

$ruleName = "Sulfur Bot Web Dashboard"

if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    Write-Host "Erstelle Firewall-Regel '$ruleName' für TCP-Port 5000..." -ForegroundColor Green
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
    Write-Host "Firewall-Regel wurde erfolgreich erstellt. Du kannst das Dashboard jetzt starten." -ForegroundColor Green
} else {
    Write-Host "Die Firewall-Regel '$ruleName' existiert bereits. Es ist keine Aktion erforderlich." -ForegroundColor Yellow
}

Read-Host "Drücke Enter, um dieses Fenster zu schließen."