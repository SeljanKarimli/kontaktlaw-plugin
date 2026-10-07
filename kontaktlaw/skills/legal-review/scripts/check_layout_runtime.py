#!/usr/bin/env python3
"""Check the local dependencies required by KontaktLaw's full Word viewer."""
from __future__ import annotations

import importlib
import json
import os
import sys


def main() -> int:
    missing = []
    for module, package in (("lxml", "lxml"), ("pymupdf", "PyMuPDF")):
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)

    word_ready = False
    word_error = None
    if os.name != "nt":
        word_error = "The native Word page viewer currently requires Windows and Microsoft Word."
    else:
        try:
            pythoncom = importlib.import_module("pythoncom")
            win32 = importlib.import_module("win32com.client")
            pythoncom.CoInitialize()
            word = None
            try:
                word = win32.DispatchEx("Word.Application")
                word.Visible = False
                word.DisplayAlerts = 0
                word_ready = True
            finally:
                if word is not None:
                    word.Quit()
                pythoncom.CoUninitialize()
        except (ImportError, OSError, Exception) as exc:
            # COM raises several implementation-specific exception classes.
            if isinstance(exc, ImportError):
                missing.append("pywin32")
            word_error = str(exc)

    result = {
        "python": sys.executable,
        "dependencies_ready": not missing,
        "missing_packages": sorted(set(missing)),
        "microsoft_word_ready": word_ready,
        "word_error": word_error,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["dependencies_ready"] and word_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
