param(
    [int]$TimeoutSeconds = 60,
    [int]$PollMilliseconds = 200
)

$ErrorActionPreference = "SilentlyContinue"

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public static class SapSe38Win32 {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetDlgCtrlID(IntPtr hwndCtl);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    public static extern IntPtr SendMessage(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);
}
"@

$CommonDialogClass = "#32770"
$StandardOkControlId = 1
$ButtonClickMessage = 0x00F5
$KnownPrompts = @(
    "A script is attempting to access SAP GUI.",
    "A script is opening a connection to system:"
)
$SapProcessNames = @("saplogon", "sapgui")
$ClickedHandles = New-Object "System.Collections.Generic.HashSet[int64]"

function Get-WindowTextValue {
    param([IntPtr]$Handle)
    $buffer = New-Object System.Text.StringBuilder 2048
    [void][SapSe38Win32]::GetWindowText($Handle, $buffer, $buffer.Capacity)
    $buffer.ToString()
}

function Get-ClassNameValue {
    param([IntPtr]$Handle)
    $buffer = New-Object System.Text.StringBuilder 256
    [void][SapSe38Win32]::GetClassName($Handle, $buffer, $buffer.Capacity)
    $buffer.ToString()
}

function Get-ProcessNameForWindow {
    param([IntPtr]$Handle)
    [uint32]$processId = 0
    [void][SapSe38Win32]::GetWindowThreadProcessId($Handle, [ref]$processId)
    if ($processId -eq 0) {
        return ""
    }
    try {
        return (Get-Process -Id $processId -ErrorAction Stop).ProcessName
    } catch {
        return ""
    }
}

function Get-ChildWindows {
    param([IntPtr]$Parent)
    $children = New-Object "System.Collections.Generic.List[IntPtr]"
    $callback = [SapSe38Win32+EnumWindowsProc]{
        param([IntPtr]$hWnd, [IntPtr]$lParam)
        [void]$children.Add($hWnd)
        return $true
    }
    [void][SapSe38Win32]::EnumChildWindows($Parent, $callback, [IntPtr]::Zero)
    $children
}

function Confirm-KnownSapSecurityPrompt {
    param([IntPtr]$WindowHandle)

    if (-not [SapSe38Win32]::IsWindowVisible($WindowHandle)) {
        return $false
    }
    if ((Get-ClassNameValue $WindowHandle) -ne $CommonDialogClass) {
        return $false
    }
    $processName = (Get-ProcessNameForWindow $WindowHandle).ToLowerInvariant()
    if ($SapProcessNames -notcontains $processName) {
        return $false
    }

    $children = @(Get-ChildWindows $WindowHandle)
    $labels = @()
    $okButton = [IntPtr]::Zero
    foreach ($child in $children) {
        $labels += Get-WindowTextValue $child
        $className = Get-ClassNameValue $child
        $controlId = [SapSe38Win32]::GetDlgCtrlID($child)
        if ($className -eq "Button" -and $controlId -eq $StandardOkControlId) {
            $okButton = $child
        }
    }

    $text = ($labels -join "`n")
    $matchesKnownPrompt = $false
    foreach ($prompt in $KnownPrompts) {
        if ($text.Contains($prompt)) {
            $matchesKnownPrompt = $true
            break
        }
    }
    if (-not $matchesKnownPrompt -or $okButton -eq [IntPtr]::Zero) {
        return $false
    }

    [void][SapSe38Win32]::SendMessage($okButton, $ButtonClickMessage, [IntPtr]::Zero, [IntPtr]::Zero)
    return $true
}

$deadline = (Get-Date).AddSeconds([Math]::Max(1, $TimeoutSeconds))
while ((Get-Date) -lt $deadline) {
    $windows = New-Object "System.Collections.Generic.List[IntPtr]"
    $callback = [SapSe38Win32+EnumWindowsProc]{
        param([IntPtr]$hWnd, [IntPtr]$lParam)
        [void]$windows.Add($hWnd)
        return $true
    }
    [void][SapSe38Win32]::EnumWindows($callback, [IntPtr]::Zero)

    foreach ($window in $windows) {
        $key = $window.ToInt64()
        if ($ClickedHandles.Contains($key)) {
            continue
        }
        if (Confirm-KnownSapSecurityPrompt $window) {
            [void]$ClickedHandles.Add($key)
        }
    }

    Start-Sleep -Milliseconds ([Math]::Max(50, $PollMilliseconds))
}
