# ULTRA

Source patch and build tooling for an unofficial Telegram iOS client. The official source and dependencies are fetched at the exact revision in `source.lock.json`; patch checksums are verified before application. This is an initial implementation, not a completed feature specification.

## Build

Run **Actions → ULTRA encrypted iOS → Run workflow** on the default branch. The workflow uses the standard `xcode-27` macOS runner and Xcode selected from the pinned upstream source. Windows can control the build and decrypt its result; an Apple signing certificate is not uploaded to CI.

Configure these repository Actions Secrets:

- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`: the application's own Telegram API parameters.
- `ULTRA_ARTIFACT_IDENTITY`: the private age identity matching `ci/artifact-recipient.txt`, used to restore encrypted intermediate artifacts inside subsequent jobs.

The repository contains only the public encryption recipient. Keep the private identity outside Git and retain a private backup. Someone with permission to change trusted workflows can access CI secrets; repository write access must remain restricted to trusted maintainers. Fork pull requests do not trigger this secret-bearing workflow.

## Validation and artifacts

The workflow runs the build-helper tests, storage/Keychain tests, diagnostic-journal tests and encrypted-artifact tests. It builds the complete simulator client, checks the visible missing-App-Group and local-storage welcome screens in a separate runner, and then compiles and inspects the iPhone IPA. Compilation does not establish GBox signing compatibility or physical-device behavior.

Build outputs, screenshots and detailed logs are uploaded only as age-encrypted ZIP bundles. Public Actions pages show step names, status and generic tool setup output. Commands that may handle API-bearing generated source write their output to encrypted private logs.

Download the artifact, extract its `.age` file and use `scripts/sealed_artifacts.py open` with the matching private identity and a new local output directory. `python scripts/sealed_artifacts.py open --help` lists the arguments. age v1.3.2 is required; its upstream macOS package is checksum-pinned by `scripts/install_age.py`. Artifacts expire after one day.

The decrypted `artifacts/ULTRA-unsigned.ipa` must be signed before installation. Its identity is `app.telegaultra.client`, displayed as ULTRA. A new installation without App Groups can explicitly choose local storage, fully close the application and reopen it. Widgets and extensions cannot share the local database; push notifications need separate compatible provisioning and APNs configuration. Existing shared storage is never silently replaced with a new local database by this patch.

## Privacy boundary

ULTRA has its own settings block below the profile. **ULTRA → Диагностика** provides an opt-in local event journal, file export, clearing, and access to existing iOS crash reports. The journal records a closed list of technical events, never free-form messages, account identifiers or credentials. It retains at most 500 events for three days, with a 64 KiB file limit; expiry is enforced at the next journal access or launch. Recording is off by default. Disabling it retains existing events until expiry or clearing. Temporary share files are removed when sharing finishes or the app next launches; copies saved by the user remain under the user's control.

Crash reports are separate from the ULTRA journal. Their explicit export contains iOS/device metadata and stack information, with a confirmation before opening the system share sheet. iOS can deliver these reports late and does not report every termination. No automatic upload is added. The existing crash-report screen also offers its own reviewed, user-confirmed sending actions.

Telegram API parameters are embedded in compiled applications. Anyone receiving a decrypted IPA may extract them. Keeping them in Actions Secrets protects source files and CI configuration; encrypting published artifacts prevents public downloads from exposing the embedded values. Do not publish decrypted binaries, private identities, generated build configuration, signing material or account/session data.

## Upstream

[TelegramMessenger/Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS), pinned revision `279f89e4d4f63f17227bf877dc3d8990f22ecd58` (13.1.2). Existing upstream copyright and license terms remain applicable to the inherited code and dependencies. This repository does not relicense upstream code. ULTRA is not an official Telegram product.
