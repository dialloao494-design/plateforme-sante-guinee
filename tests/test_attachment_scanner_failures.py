"""An explicitly requested upload scanner must never silently disable itself."""
import subprocess
import sys

import pytest
from fastapi import HTTPException

from services.secure_attachment_storage import SecureAttachmentStorage


@pytest.mark.parametrize("failure", ["unknown-mode", "timeout"])
def test_scanner_configuration_or_timeout_fails_closed(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("SECURE_ATTACHMENT_ROOT", str(tmp_path / "attachments"))
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "clamav" if failure == "timeout" else "misspelled-mode")
    if failure == "timeout":
        monkeypatch.setitem(sys.modules, "pyclamd", None)
        monkeypatch.setattr("core.attachment_malware.shutil.which", lambda _: "/synthetic/clamscan")

        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("synthetic-clamscan", 60)

        monkeypatch.setattr("core.attachment_malware.subprocess.run", timeout)
    with pytest.raises(HTTPException) as exc:
        SecureAttachmentStorage.store(b"%PDF-1.4\nsynthetic", original_filename="clean.pdf", extension=".pdf")
    assert exc.value.status_code == 503
    assert not (tmp_path / "attachments").exists()
