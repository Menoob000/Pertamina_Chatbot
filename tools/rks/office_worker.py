"""Isolated Windows Word renderer. Invoked in a bounded subprocess."""
import json
from pathlib import Path
import sys


def main():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.AutomationSecurity = 3
        path = Path(sys.argv[1]).resolve()
        document = word.Documents.Open(str(path), ReadOnly=False, AddToRecentFiles=False)
        document.Repaginate()
        document.Fields.Update()
        for toc in document.TablesOfContents:
            toc.Update()
        document.Repaginate()
        for toc in document.TablesOfContents:
            toc.UpdatePageNumbers()
        document.Save()
        # Verify each TOC hyperlink against the target bookmark's real page.
        mismatches = []
        entries = 0
        for toc in document.TablesOfContents:
            for link in toc.Range.Hyperlinks:
                anchor = link.SubAddress
                if anchor and document.Bookmarks.Exists(anchor):
                    target = document.Bookmarks.Item(anchor).Range.Information(3)
                    text = link.Range.Paragraphs.Item(1).Range.Text.strip()
                    tail = text.rsplit("\t", 1)[-1].strip()
                    if tail.isdigit():
                        entries += 1
                        if int(tail) != target:
                            mismatches.append({"entry": text, "actual": target})
        document.ExportAsFixedFormat(str(path.with_suffix(".pdf")), 17)
        Path(sys.argv[2]).write_text(json.dumps({"engine": "word", "toc_entries_checked": entries,
                                                "toc_mismatches": mismatches}), encoding="utf-8")
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
