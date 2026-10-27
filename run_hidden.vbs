' Starts HTML Drop with no window. Used at login by setup_office_pc.ps1.
' Runs python.exe, the same program as the other dashboard servers, so the
' firewall treats it the same way. Output goes to server.log in this folder.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c python -u server.py >> server.log 2>&1", 0, False
