from pathlib import Path
from src.services.file_service import FileService
from src.ai_tools.models.file_spec import FileSpec


def test_create_and_read_files(tmp_path):
    fs = FileService()
    files = [FileSpec(path="subdir/file.txt", fileContent="hello world")]
    created = fs.create_files(str(tmp_path), files)
    expected = tmp_path / "subdir" / "file.txt"
    assert Path(created[0]) == expected
    assert expected.exists()
    content = fs.read_file(str(expected))
    assert content == "hello world"
