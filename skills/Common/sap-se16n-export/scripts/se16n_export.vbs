' Export an SE16N table result to XLSX through SAP GUI Scripting.
' Usage:
'   cscript //nologo se16n_export.vbs /table:MARA /maxhits:100 /outdir:"<LOCAL_WORKSPACE>\se16n" /file:"mara.xlsx"
Option Explicit

Dim tableName
Dim maxHits
Dim outputDir
Dim outputFile
Dim defaultOutputDir
Dim securityHelper
Dim securityTimeout
Dim fso
Dim SapGuiAuto
Dim application
Dim connection
Dim session

Set fso = CreateObject("Scripting.FileSystemObject")
defaultOutputDir = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "output")

tableName = UCase(Trim(GetNamedArg("table", "MARA")))
maxHits = Trim(GetNamedArg("maxhits", "2147483647"))
outputDir = TrimTrailingSlash(Trim(GetNamedArg("outdir", defaultOutputDir)))
outputFile = Trim(GetNamedArg("file", LCase(tableName) & ".xlsx"))
securityHelper = LCase(Trim(GetNamedArg("securityhelper", "true")))
securityTimeout = Trim(GetNamedArg("securitytimeout", "60"))

If Len(tableName) = 0 Then Fail "Missing /table value."
If Len(maxHits) = 0 Or Not IsNumeric(maxHits) Then Fail "Missing or invalid /maxhits value."
If Len(outputDir) = 0 Then Fail "Missing /outdir value."
If Len(outputFile) = 0 Then Fail "Missing /file value."
If Len(securityTimeout) = 0 Or Not IsNumeric(securityTimeout) Then Fail "Missing or invalid /securitytimeout value."
If InStrRev(outputFile, ".") = 0 Then outputFile = outputFile & ".xlsx"

CreateFolderRecursive outputDir
If securityHelper <> "false" Then StartSecurityPromptHelper CLng(securityTimeout)

On Error Resume Next
Set SapGuiAuto = GetObject("SAPGUI")
If Err.Number <> 0 Or Not IsObject(SapGuiAuto) Then Fail "SAP GUI is not running or scripting is unavailable."
Err.Clear
Set application = SapGuiAuto.GetScriptingEngine
If Err.Number <> 0 Or Not IsObject(application) Then Fail "Could not obtain SAP GUI scripting engine."
Err.Clear
Set connection = application.Children(0)
If Err.Number <> 0 Or Not IsObject(connection) Then Fail "No SAP GUI connection is available."
Err.Clear
Set session = connection.Children(0)
If Err.Number <> 0 Or Not IsObject(session) Then Fail "No SAP GUI session is available."
On Error GoTo 0

If IsObject(WScript) Then
   WScript.ConnectObject session, "on"
   WScript.ConnectObject application, "on"
End If

session.findById("wnd[0]").maximize
session.findById("wnd[0]/tbar[0]/okcd").text = "/nse16n"
session.findById("wnd[0]").sendVKey 0
session.findById("wnd[0]/usr/ctxtGD-TAB").text = tableName
session.findById("wnd[0]").sendVKey 0
session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = maxHits
session.findById("wnd[0]/usr/txtGD-MAX_LINES").setFocus
session.findById("wnd[0]/usr/txtGD-MAX_LINES").caretPosition = Len(maxHits)
session.findById("wnd[0]").sendVKey 0
session.findById("wnd[0]/tbar[1]/btn[8]").press
session.findById("wnd[0]/shellcont/shell").pressToolbarContextButton "&MB_EXPORT"
session.findById("wnd[0]/shellcont/shell").selectContextMenuItem "&XXL"
session.findById("wnd[1]/tbar[0]/btn[20]").press
session.findById("wnd[1]/usr/ctxtDY_PATH").text = outputDir
session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = outputFile
session.findById("wnd[1]/usr/ctxtDY_FILENAME").caretPosition = Len(outputFile)
session.findById("wnd[1]/tbar[0]/btn[0]").press

WScript.Echo "SE16N export submitted: " & outputDir & "\" & outputFile

Function GetNamedArg(name, defaultValue)
   If WScript.Arguments.Named.Exists(name) Then
      GetNamedArg = WScript.Arguments.Named.Item(name)
   Else
      GetNamedArg = defaultValue
   End If
End Function

Function TrimTrailingSlash(value)
   Do While Len(value) > 3 And Right(value, 1) = "\"
      value = Left(value, Len(value) - 1)
   Loop
   TrimTrailingSlash = value
End Function

Function QuoteArg(value)
   QuoteArg = """" & Replace(value, """", """""") & """"
End Function

Sub StartSecurityPromptHelper(timeoutSeconds)
   Dim helperPath
   Dim shell
   Dim command

   helperPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "sap_security_prompt_helper.ps1")
   If Not fso.FileExists(helperPath) Then Exit Sub

   Set shell = CreateObject("WScript.Shell")
   command = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File " & _
      QuoteArg(helperPath) & " -TimeoutSeconds " & CStr(timeoutSeconds)

   On Error Resume Next
   shell.Run command, 0, False
   If Err.Number <> 0 Then
      WScript.Echo "WARN: Could not start SAP security prompt helper: " & Err.Description
      Err.Clear
   End If
   On Error GoTo 0
End Sub

Sub CreateFolderRecursive(pathValue)
   Dim parentPath
   If fso.FolderExists(pathValue) Then Exit Sub
   parentPath = fso.GetParentFolderName(pathValue)
   If Len(parentPath) > 0 And Not fso.FolderExists(parentPath) Then
      CreateFolderRecursive parentPath
   End If
   On Error Resume Next
   fso.CreateFolder pathValue
   If Err.Number <> 0 Then Fail "Could not create output directory: " & pathValue & " (" & Err.Description & ")"
   On Error GoTo 0
End Sub

Sub Fail(message)
   On Error Resume Next
   WScript.StdErr.WriteLine "ERROR: " & message
   If Err.Number <> 0 Then
      Err.Clear
      WScript.Echo "ERROR: " & message
   End If
   WScript.Quit 1
End Sub
