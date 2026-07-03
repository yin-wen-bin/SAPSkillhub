' Download an ABAP program source file through SAP GUI Scripting and SE38.
' Usage:
'   cscript //nologo se38_export.vbs /program:SAPLSE16N /out:"<LOCAL_WORKSPACE>\abap\SAPLSE16N.abap"
Option Explicit

Dim programName
Dim outputPath
Dim outputDir
Dim outputFile
Dim securityHelper
Dim securityTimeout
Dim fso
Dim SapGuiAuto
Dim application
Dim connection
Dim session

Set fso = CreateObject("Scripting.FileSystemObject")

programName = UCase(Trim(GetRequiredArg("program", 0, "program")))
outputPath = Trim(GetRequiredArg("out", 1, "out"))
securityHelper = LCase(Trim(GetNamedArg("securityhelper", "true")))
securityTimeout = Trim(GetNamedArg("securitytimeout", "60"))

If Len(programName) = 0 Then Fail "Missing /program value."
If Len(outputPath) = 0 Then Fail "Missing /out value."
If Len(securityTimeout) = 0 Or Not IsNumeric(securityTimeout) Then Fail "Missing or invalid /securitytimeout value."

ResolveOutputPath outputPath, programName, outputDir, outputFile
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
session.findById("wnd[0]/tbar[0]/okcd").text = "/nse38"
session.findById("wnd[0]").sendVKey 0
session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = programName
session.findById("wnd[0]/usr/radRS38M-FUNC_EDIT").setFocus
session.findById("wnd[0]/usr/btnSHOP").press
session.findById("wnd[0]/mbar/menu[3]/menu[9]/menu[3]/menu[1]").select
session.findById("wnd[1]/usr/ctxtDY_PATH").text = outputDir
session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = outputFile
session.findById("wnd[1]/usr/ctxtDY_FILE_ENCODING").setFocus
session.findById("wnd[1]/usr/ctxtDY_FILE_ENCODING").caretPosition = 0
session.findById("wnd[1]").sendVKey 4
session.findById("wnd[2]/tbar[0]/btn[12]").press
session.findById("wnd[1]/tbar[0]/btn[0]").press

WScript.Echo "SE38 export submitted: " & fso.BuildPath(outputDir, outputFile)

Function GetRequiredArg(name, position, displayName)
   If WScript.Arguments.Named.Exists(name) Then
      GetRequiredArg = WScript.Arguments.Named.Item(name)
   ElseIf WScript.Arguments.Unnamed.Count > position Then
      GetRequiredArg = WScript.Arguments.Unnamed.Item(position)
   Else
      Fail "Missing /" & displayName & " value."
   End If
End Function

Function GetNamedArg(name, defaultValue)
   If WScript.Arguments.Named.Exists(name) Then
      GetNamedArg = WScript.Arguments.Named.Item(name)
   Else
      GetNamedArg = defaultValue
   End If
End Function

Sub ResolveOutputPath(pathValue, sourceProgramName, outputDirRef, outputFileRef)
   Dim normalized
   Dim parentPath
   Dim fileName

   normalized = Replace(pathValue, "/", "\")
   If EndsWithSlash(normalized) Or fso.FolderExists(normalized) Then
      outputDirRef = TrimTrailingSlash(normalized)
      outputFileRef = SanitizeFileName(sourceProgramName)
      Exit Sub
   End If

   parentPath = fso.GetParentFolderName(normalized)
   fileName = fso.GetFileName(normalized)

   If Len(parentPath) = 0 Then
      outputDirRef = TrimTrailingSlash(fso.GetAbsolutePathName("."))
   Else
      outputDirRef = TrimTrailingSlash(parentPath)
   End If
   outputFileRef = fileName

   If Len(outputFileRef) = 0 Then
      outputFileRef = SanitizeFileName(sourceProgramName)
   End If
End Sub

Function EndsWithSlash(value)
   EndsWithSlash = (Right(value, 1) = "\")
End Function

Function TrimTrailingSlash(value)
   Do While Len(value) > 3 And Right(value, 1) = "\"
      value = Left(value, Len(value) - 1)
   Loop
   TrimTrailingSlash = value
End Function

Function SanitizeFileName(value)
   Dim invalidChars
   Dim index
   invalidChars = Array("\", "/", ":", "*", "?", """", "<", ">", "|")
   For index = 0 To UBound(invalidChars)
      value = Replace(value, invalidChars(index), "_")
   Next
   value = Trim(value)
   If Len(value) = 0 Then Fail "Could not derive an output filename from /program."
   SanitizeFileName = value
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
