import logging
from unittest.mock import MagicMock, patch

from src.configuration.config import Config
from src.ai_tools.models.file_spec import FileSpec
from src.services.command_service import CommandService, build_typescript_compiler_command


def test_build_typescript_compiler_command():
    files = [
        FileSpec(path="src/a.ts", fileContent=""),
        FileSpec(path="src/b.ts", fileContent=""),
    ]
    expected = (
        "npx tsc src/a.ts src/b.ts "
        "--lib es2021 "
        "--module NodeNext "
        "--target ESNext "
        "--strict "
        "--esModuleInterop "
        "--skipLibCheck "
        "--forceConsistentCasingInFileNames "
        "--moduleResolution nodenext "
        "--allowUnusedLabels false "
        "--allowUnreachableCode false "
        "--noFallthroughCasesInSwitch "
        "--noImplicitOverride "
        "--noImplicitReturns "
        "--noPropertyAccessFromIndexSignature "
        "--noUncheckedIndexedAccess "
        "--noUnusedLocals "
        "--noUnusedParameters "
        "--checkJs "
        "--noEmit "
        "--strictNullChecks false "
        "--excludeDirectories node_modules"
    )
    assert build_typescript_compiler_command(files) == expected


def test_run_command_with_popen_mock(tmp_path):
    config = Config(destination_folder=str(tmp_path))
    service = CommandService(config, logger=logging.getLogger(__name__))

    process_mock = MagicMock()
    process_mock.stdout.readline.side_effect = ["line1\n", "line2\n", ""]
    process_mock.poll.return_value = 0
    process_mock.returncode = 0

    with patch("src.services.command_service.subprocess.Popen", return_value=process_mock) as mock_popen:
        success, output = service.run_command("dummy")
        mock_popen.assert_called_once()

    assert success is True
    assert output == "line1\nline2"
