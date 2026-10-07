"""Export with an isolated, invisible Microsoft Word instance; never save source."""
import sys
import pythoncom
import win32com.client


def export(source, target):
    pythoncom.CoInitialize()
    word = document = None
    try:
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3
        word.Options.UpdateLinksAtOpen = False
        document = word.Documents.Open(source, ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False)
        document.ExportAsFixedFormat(target, 17)
    finally:
        if document is not None:
            document.Close(0)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


if __name__ == '__main__':
    export(sys.argv[1], sys.argv[2])
