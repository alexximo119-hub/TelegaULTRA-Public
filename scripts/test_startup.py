"""Run storage, diagnostic journal and PasscodeCore tests without UI dependencies."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> None:
    if sys.platform != 'darwin':
        raise RuntimeError('Startup tests require macOS Security and LocalAuthentication')
    source = Path(__file__).resolve().parents[1] / 'source'
    with tempfile.TemporaryDirectory(prefix='ultra-startup-tests-') as directory:
        package = Path(directory)
        targets = {
            'Sources/UltraStartupPolicy': [source / 'submodules/TelegramUI/Sources/UltraAppStorage.swift'],
            'Tests/UltraStartupPolicyTests': [source / 'Tests/UltraAppStorageTests/UltraAppStorageTests.swift'],
            'Sources/UltraDiagnostics': [
                source / 'submodules/TelegramUIPreferences/Sources'
                / 'UltraDiagnosticsStore.swift',
            ],
            'Tests/UltraDiagnosticsTests': [
                source / 'Tests/UltraDiagnosticsTests/UltraDiagnosticsTests.swift',
            ],
            'Sources/PasscodeCore': [source / 'submodules/PasscodeCore/Sources' / name for name in (
                'Passcode.swift', 'PasscodeCrypto.swift', 'PasscodeKeychainScope.swift',
            )],
            'Tests/PasscodeCoreTests': list((source / 'submodules/PasscodeCore/Tests/PasscodeCoreTests').glob('*.swift')),
        }
        for target, files in targets.items():
            output = package / target
            output.mkdir(parents=True)
            for path in files:
                shutil.copyfile(path, output / path.name)
        dependency = json.dumps(str(source / 'submodules/SSignalKit'))
        manifest = '''// swift-tools-version:5.9
import PackageDescription
let package = Package(
    name: "UltraStartupTests",
    platforms: [.macOS(.v13)],
    dependencies: [.package(path: DEPENDENCY)],
    targets: [
        .target(name: "UltraStartupPolicy"),
        .testTarget(name: "UltraStartupPolicyTests", dependencies: ["UltraStartupPolicy"]),
        .target(name: "UltraDiagnostics"),
        .testTarget(name: "UltraDiagnosticsTests", dependencies: ["UltraDiagnostics"]),
        .target(name: "PasscodeCore", dependencies: [.product(name: "SwiftSignalKit", package: "SSignalKit")]),
        .testTarget(name: "PasscodeCoreTests", dependencies: ["PasscodeCore"])
    ]
)
'''.replace('DEPENDENCY', dependency)
        (package / 'Package.swift').write_text(manifest, encoding='utf-8')
        subprocess.run(['swift', 'test', '--package-path', str(package)], check=True)


if __name__ == '__main__':
    main()
