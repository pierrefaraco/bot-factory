import io
import os
from unittest.mock import MagicMock

import pytest

from src.services.knowledge_svc import InvalidPdfError, KnowledgeSvc

PDF_BYTES = b"%PDF-1.4 fake"


@pytest.fixture
def svc(tmp_path):
    knowledge_svc = KnowledgeSvc(MagicMock(), MagicMock())
    knowledge_svc.upload_folder = str(tmp_path)
    return knowledge_svc


def test_same_name_uploads_never_collide(svc, tmp_path):
    first = svc.save_pdf(1, "cv.pdf", io.BytesIO(PDF_BYTES + b" first"))
    second = svc.save_pdf(2, "cv.pdf", io.BytesIO(PDF_BYTES + b" second"))

    assert first != second
    assert first.startswith("1" + os.sep) and second.startswith("2" + os.sep)
    assert (tmp_path / first).read_bytes().endswith(b"first")
    assert (tmp_path / second).read_bytes().endswith(b"second")


def test_rejected_upload_leaves_existing_file_alone(svc, tmp_path):
    kept = svc.save_pdf(1, "cv.pdf", io.BytesIO(PDF_BYTES))

    with pytest.raises(InvalidPdfError):
        svc.save_pdf(1, "cv.pdf", io.BytesIO(b"not a pdf"))

    assert (tmp_path / kept).exists()
    assert os.listdir(tmp_path / "1") == [os.path.basename(kept)]


def test_uploaded_name_is_never_part_of_the_path(svc):
    stored = svc.save_pdf(1, "../../etc/evil.pdf", io.BytesIO(PDF_BYTES))
    assert "evil" not in stored and ".." not in stored


@pytest.mark.parametrize(
    "name, expected",
    [("cv.pdf", "cv.pdf"), ("../../x.pdf", "x.pdf"), ("C:\\docs\\a.pdf", "a.pdf"), (None, "")],
)
def test_display_name(name, expected):
    assert KnowledgeSvc._display_name(name) == expected
