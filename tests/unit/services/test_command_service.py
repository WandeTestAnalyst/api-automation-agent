from src.services.command_service import build_typescript_compiler_command
from src.ai_tools.models.file_spec import FileSpec


def test_build_typescript_compiler_command():
    files = [
        FileSpec(path="src/a.ts", fileContent=""),
        FileSpec(path="src/b.ts", fileContent=""),
    ]
    cmd = build_typescript_compiler_command(files)
    assert cmd.startswith("npx tsc src/a.ts src/b.ts")
    assert "--noEmit" in cmd
