Option Explicit

' =============================================================
' SCA Time Automation - Calendar Export (Standalone VBS)
' Run from terminal: cscript //Nologo scripts/calendar_export.vbs [WEEKS]
' Example: cscript //Nologo scripts/calendar_export.vbs 12
' =============================================================

' --- Configuration ---
Dim WEEKS_BACK
If WScript.Arguments.Count > 0 Then
    WEEKS_BACK = CInt(WScript.Arguments(0))
Else
    WEEKS_BACK = 4
End If

Const OUTPUT_PATH = "C:\Users\1028120\Documents\Scripts\corp-sca-time-automation\data\input\calendar_export.json"
Const INTERNAL_DOMAINS = "blueyonder.com,jda.com,microsoft.com"

' --- Variables ---
Dim objOutlook, objExchUser, ns, calendarFolder, items, filteredItems, appt, recip
Dim stream
Dim startDate, endDate, filterStr
Dim jsonStr, comma, category, externalDomains
Dim recipEmail, recipDomain
Dim cats, cat, internalArr
Dim eventCount, i, isInternal

' --- Connect to Outlook via COM ---
On Error Resume Next
Set objOutlook = CreateObject("Outlook.Application")
If Err.Number <> 0 Then
    WScript.Echo "ERROR: Cannot connect to Outlook. Is it running?"
    WScript.Quit 1
End If
On Error GoTo 0

Set ns = objOutlook.GetNamespace("MAPI")
Set calendarFolder = ns.GetDefaultFolder(9) ' olFolderCalendar = 9

' --- Setup dates ---
endDate = DateAdd("d", 1, Date)
startDate = DateAdd("ww", -WEEKS_BACK, Date)

WScript.Echo "Exporting calendar..."
WScript.Echo "  From: " & startDate
WScript.Echo "  To:   " & endDate
WScript.Echo "  Weeks back: " & WEEKS_BACK

' Parse internal domains
internalArr = Split(INTERNAL_DOMAINS, ",")

' --- Get calendar items ---
Set items = calendarFolder.Items
items.Sort "[Start]", False
items.IncludeRecurrences = True
filterStr = "[Start] >= '" & FormatDateTime(startDate, 2) & "' AND [Start] < '" & FormatDateTime(endDate, 2) & "'"
Set filteredItems = items.Restrict(filterStr)

' --- Build JSON string ---
jsonStr = "{""events"": ["
comma = ""
eventCount = 0

' --- Process events ---
For Each appt In filteredItems

    ' Extract category (with . prefix)
    category = ""
    If Len(appt.Categories) > 0 Then
        cats = Split(appt.Categories, ",")
        For Each cat In cats
            cat = Trim(cat)
            If Left(cat, 1) = "." Then
                category = Mid(cat, 2)
                Exit For
            End If
        Next
    End If

    ' Skip if no tracked category
    If category = "" Then
        ' Continue to next
    Else
        ' Get external domains from recipients
        externalDomains = ""
        On Error Resume Next
        For Each recip In appt.Recipients
            recipEmail = ""

            ' Try to get SMTP address
            ' 0 = olExchangeUserAddressEntry, 5 = olExchangeRemoteUserAddressEntry
            If recip.AddressEntry.AddressEntryUserType = 0 Or _
               recip.AddressEntry.AddressEntryUserType = 5 Then
                Set objExchUser = recip.AddressEntry.GetExchangeUser
                If Not objExchUser Is Nothing Then
                    recipEmail = objExchUser.PrimarySmtpAddress
                End If
            ' 30 = olSmtpAddressEntry
            ElseIf recip.AddressEntry.AddressEntryUserType = 30 Then
                recipEmail = recip.AddressEntry.Address
            End If

            ' Extract domain
            If InStr(recipEmail, "@") > 0 Then
                recipDomain = LCase(Mid(recipEmail, InStr(recipEmail, "@") + 1))

                ' Check if external
                isInternal = False
                For i = LBound(internalArr) To UBound(internalArr)
                    If recipDomain = Trim(internalArr(i)) Then
                        isInternal = True
                        Exit For
                    End If
                Next

                ' Add if external and not already in list
                If Not isInternal And recipDomain <> "" Then
                    If InStr(externalDomains, recipDomain) = 0 Then
                        If externalDomains <> "" Then externalDomains = externalDomains & ","
                        externalDomains = externalDomains & recipDomain
                    End If
                End If
            End If
        Next
        On Error GoTo 0

        ' Build JSON for this event
        jsonStr = jsonStr & comma & "{" & vbCrLf
        jsonStr = jsonStr & "  ""start"": """ & FormatDate(appt.Start) & """," & vbCrLf
        jsonStr = jsonStr & "  ""end"": """ & FormatDate(appt.End) & """," & vbCrLf
        jsonStr = jsonStr & "  ""category"": """ & UCase(category) & """," & vbCrLf
        jsonStr = jsonStr & "  ""title"": """ & CleanString(appt.Subject) & """," & vbCrLf
        jsonStr = jsonStr & "  ""minutes"": " & DateDiff("n", appt.Start, appt.End) & "," & vbCrLf
        jsonStr = jsonStr & "  ""all_day"": " & LCase(appt.AllDayEvent) & "," & vbCrLf
        jsonStr = jsonStr & "  ""external_domains"": """ & externalDomains & """," & vbCrLf
        jsonStr = jsonStr & "  ""location"": """ & CleanString(appt.Location) & """," & vbCrLf
        jsonStr = jsonStr & "  ""recipients"": " & appt.Recipients.Count & "," & vbCrLf
        jsonStr = jsonStr & "  ""busy_status"": " & appt.BusyStatus & vbCrLf
        jsonStr = jsonStr & "}"

        comma = ","
        eventCount = eventCount + 1
    End If
Next

' --- Close JSON ---
jsonStr = jsonStr & vbCrLf & "]," & vbCrLf
jsonStr = jsonStr & """export_date"": """ & FormatDate(Now) & """," & vbCrLf
jsonStr = jsonStr & """weeks_back"": " & WEEKS_BACK & "," & vbCrLf
jsonStr = jsonStr & """event_count"": " & eventCount & vbCrLf
jsonStr = jsonStr & "}"

' --- Write as UTF-8 ---
Set stream = CreateObject("ADODB.Stream")
stream.Open
stream.Type = 2  ' Text
stream.Charset = "utf-8"
stream.WriteText jsonStr
stream.SaveToFile OUTPUT_PATH, 2  ' Overwrite
stream.Close

WScript.Echo ""
WScript.Echo "Export complete!"
WScript.Echo "  Events: " & eventCount
WScript.Echo "  File: " & OUTPUT_PATH

' --- Cleanup ---
Set stream = Nothing
Set filteredItems = Nothing
Set items = Nothing
Set calendarFolder = Nothing
Set ns = Nothing
Set objOutlook = Nothing

WScript.Quit 0

' =============================================================
' Helper Functions
' =============================================================

Function CleanString(ByVal str)
    str = Replace(str, "\", "\\")
    str = Replace(str, """", "\""")
    str = Replace(str, vbCrLf, " ")
    str = Replace(str, vbCr, " ")
    str = Replace(str, vbLf, " ")
    str = Replace(str, vbTab, " ")
    CleanString = str
End Function

Function FormatDate(ByVal dt)
    FormatDate = Year(dt) & "-" & Right("0" & Month(dt), 2) & "-" & Right("0" & Day(dt), 2) & " " & Right("0" & Hour(dt), 2) & ":" & Right("0" & Minute(dt), 2)
End Function
