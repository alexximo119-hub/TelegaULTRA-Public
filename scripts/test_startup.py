"""Run storage, diagnostic journal and PasscodeCore tests without UI dependencies."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
            'Sources/UltraSettingsPolicies': [
                source / 'submodules/TelegramUIPreferences/Sources/UltraSettings.swift',
                source / 'submodules/TelegramUIPreferences/Sources/UltraInteractionPolicy.swift',
                source / 'submodules/TelegramUIPreferences/Sources/UltraDeviceIdentity.swift',
                source / 'submodules/TelegramUIPreferences/Sources/UltraLocationSelection.swift',
                source / 'submodules/TelegramUIPreferences/Sources/UltraProfileDatePolicy.swift',
                source / 'submodules/TelegramUIPreferences/Sources/UltraLocalDisplayValues.swift',
                source / 'submodules/TelegramUIPreferences/Sources/UltraViewOnceSavePolicy.swift',
                source / 'submodules/TelegramCore/Sources/State/AccountPresencePolicy.swift',
                source / 'submodules/TelegramCore/Sources/State/AccountInputActivityPolicy.swift',
                source / 'submodules/TelegramCore/Sources/Settings/AccountContentRestrictionPolicy.swift',
                source / 'submodules/TelegramCore/Sources/Settings/UltraAccountLoadPolicy.swift',
                source / 'submodules/TelegramCore/Sources/Settings/UltraAccountDirectoryStore.swift',
                source / 'submodules/TelegramCore/Sources/Network/AccountUploadMode.swift',
                source / 'submodules/TelegramCore/Sources/Network/AccountImageUploadPrivacy.swift',
            ],
            'Tests/UltraSettingsTests': list(
                (source / 'Tests/UltraSettingsTests').glob('*.swift')
            ),
            'Sources/UltraFontPolicy': [
                source / 'submodules/Display/Source/UltraFontFilePolicy.swift',
            ],
            'Tests/UltraFontPolicyTests': list(
                (source / 'Tests/UltraFontTests').glob('*.swift')
            ),
            'Sources/UltraFolderLayout': [
                source / 'submodules/ChatListUI/Sources/UltraFolderTabsLayout.swift',
            ],
            'Tests/UltraFolderLayoutTests': list(
                (source / 'Tests/UltraFolderTabsTests').glob('*.swift')
            ),
            'Sources/UltraHistoryModels': [
                source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages'
                / 'UltraLocalHistoryModels.swift',
                source / 'submodules/TelegramCore/Sources/TelegramEngine/Messages'
                / 'UltraLocalHistoryCipher.swift',
            ],
            'Tests/UltraHistoryModelsTests': list(
                (source / 'Tests/UltraHistoryTests').glob('*.swift')
            ),
            'Sources/UltraSessionFormats': [
                source / 'submodules/TelegramCore/Sources/TelegramEngine/Auth'
                / 'UltraSessionImportData.swift',
                source / 'submodules/TelegramCore/Sources/TelegramEngine/Auth'
                / 'UltraSessionSQLiteReader.swift',
                source / 'submodules/TelegramCore/Sources/TelegramEngine/Auth'
                / 'UltraTDataFormat.swift',
            ],
            'Tests/UltraSessionFormatsTests': list(
                (source / 'Tests/UltraSessionImportTests').glob('*.swift')
            ),
            'Sources/UltraVideoPreparing': [source / 'submodules/TelegramCore/Sources/PendingMessages' / name for name in ('UltraVideoPreparationPolicy.swift', 'UltraVideoSanitizer.swift')],
            'Tests/UltraVideoPreparationTests': list((source / 'Tests/UltraVideoPreparationTests').glob('*.swift')),
            'Sources/UltraImageSanitizing': [
                source / 'submodules/TelegramCore/Sources/PendingMessages/UltraImageSanitizer.swift',
            ],
            'Tests/UltraImageSanitizerTests': list(
                (source / 'Tests/UltraImageSanitizerTests').glob('*.swift')
            ),
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
        .target(name: "UltraSettingsPolicies"),
        .testTarget(name: "UltraSettingsTests", dependencies: ["UltraSettingsPolicies"]),
        .target(name: "UltraFontPolicy"),
        .testTarget(name: "UltraFontPolicyTests", dependencies: ["UltraFontPolicy"]),
        .target(name: "UltraFolderLayout"),
        .testTarget(name: "UltraFolderLayoutTests", dependencies: ["UltraFolderLayout"]),
        .target(name: "UltraHistoryModels"),
        .testTarget(name: "UltraHistoryModelsTests", dependencies: ["UltraHistoryModels"]),
        .target(name: "UltraSessionFormats", linkerSettings: [.linkedLibrary("sqlite3")]),
        .testTarget(name: "UltraSessionFormatsTests", dependencies: ["UltraSessionFormats"]),
        .target(name: "UltraVideoPreparing"),
        .testTarget(name: "UltraVideoPreparationTests", dependencies: ["UltraVideoPreparing"]),
        .target(name: "UltraImageSanitizing"),
        .testTarget(name: "UltraImageSanitizerTests", dependencies: ["UltraImageSanitizing"]),
        .target(name: "PasscodeCore", dependencies: [.product(name: "SwiftSignalKit", package: "SSignalKit")]),
        .testTarget(name: "PasscodeCoreTests", dependencies: ["PasscodeCore"])
    ]
)
'''.replace('DEPENDENCY', dependency)
        (package / 'Package.swift').write_text(manifest, encoding='utf-8')
        subprocess.run(['swift', 'test', '--package-path', str(package)], check=True)


if __name__ == '__main__':
    main()
