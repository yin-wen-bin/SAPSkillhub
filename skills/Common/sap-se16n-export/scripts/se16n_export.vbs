' Compatibility wrapper for the Python SE16N entry point.
' Existing named arguments are preserved. Explicit /maxhits implies full mode;
' omitting it uses validate mode with 100 rows.
Option Explicit

Dim fso, shell, scriptDir, pythonScript, command, key, exitCode
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonScript = fso.BuildPath(scriptDir, "se16n_export.py")
command = "python " & QuoteArg(pythonScript)

AppendNamed "table", "--table"
AppendNamed "outdir", "--output-dir"
AppendNamed "file", "--file"
AppendNamed "maxhits", "--maxhits"
If WScript.Arguments.Named.Exists("overwrite") Then
  If LCase(CStr(WScript.Arguments.Named.Item("overwrite"))) = "true" Then command = command & " --overwrite"
End If

If WScript.Arguments.Named.Exists("securityhelper") Or WScript.Arguments.Named.Exists("securitytimeout") Then
  WScript.Echo "WARN: securityhelper/securitytimeout are deprecated; the Python entry fails closed on unknown dialogs."
End If

exitCode = shell.Run(command, 1, True)
WScript.Quit exitCode

Sub AppendNamed(vbsName, cliName)
  If WScript.Arguments.Named.Exists(vbsName) Then
    command = command & " " & cliName & " " & QuoteArg(CStr(WScript.Arguments.Named.Item(vbsName)))
  End If
End Sub

Function QuoteArg(value)
  QuoteArg = Chr(34) & Replace(value, Chr(34), Chr(34) & Chr(34)) & Chr(34)
End Function
