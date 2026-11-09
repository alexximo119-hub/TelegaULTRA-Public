# ULTRA

Source patch and build tooling for an unofficial Telegram iOS client. The official source and dependencies are fetched at the exact revision in `source.lock.json`; patch checksums are verified before application. The local 13.2 overlay contains additional settings, bounded local history, own-session import, local display changes and media preparation. New code requires native compilation and device validation; this is not a claim that every specification item is supported.

## Build

Run **Actions → ULTRA encrypted iOS → Run workflow** on the default branch. The workflow uses the standard `xcode-27` macOS runner and Xcode selected from the pinned upstream source. Windows can control the build and decrypt its result; an Apple signing certificate is not uploaded to CI.

Configure these repository Actions Secrets:

- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`: the application's own Telegram API parameters.
- `ULTRA_ARTIFACT_IDENTITY`: the private age identity matching `ci/artifact-recipient.txt`, used to restore encrypted intermediate artifacts inside subsequent jobs.

The repository contains only the public encryption recipient. Keep the private identity outside Git and retain a private backup. Someone with permission to change trusted workflows can access CI secrets; repository write access must remain restricted to trusted maintainers. Fork pull requests do not trigger this secret-bearing workflow.

## Validation and artifacts

The workflow runs the build-helper tests, standalone storage/Keychain, policy/model, media-preparation and diagnostic tests, and encrypted-artifact tests. After simulator compilation it explicitly runs the native TelegramCoreTests and PostboxTests targets on the pinned iPhone 17 / iOS 27.0 runner; failures block release. Simulator and iPhone compilation can run independently when runner capacity is available. A separate simulator job checks the visible missing-App-Group and local-storage welcome screens. Final release assembly requires successful startup verification and the device candidate. Compilation does not establish GBox signing compatibility or physical-device behavior.

The compilation wrapper emits a fixed progress label and elapsed time every minute; detailed command output stays in private logs. Device and startup intermediates use distinct encrypted artifacts. The final `ULTRA-iOS-<number>-encrypted` bundle includes the device output and startup evidence. On failure, an encrypted log bundle may still be uploaded; artifact existence alone is not a successful release. No measured reduction in build time is claimed.

Build outputs, screenshots and detailed logs are uploaded only as age-encrypted ZIP bundles. Public Actions pages show step names, status and generic tool setup output. Commands that may handle API-bearing generated source write their output to encrypted private logs.

Encrypted uploads have up to three attempts, separated by 20-second pauses. The last failed attempt fails the job. The manual **Recover ULTRA build 16** workflow recompiles only the iPhone version using the exact patch already tested in run `42395019220`; it requires the unexpired encrypted startup artifact from that run and refuses a different patch. This recovery does not rerun simulator validation. A failed upload after a finished hosted job does not leave a downloadable copy of that job's local files.

Download the artifact, extract its `.age` file and use `scripts/sealed_artifacts.py open` with the matching private identity and a new local output directory. `python scripts/sealed_artifacts.py open --help` lists the arguments. age v1.3.2 is required; its upstream macOS package is checksum-pinned by `scripts/install_age.py`. Artifacts expire after one day.

The decrypted `artifacts/ULTRA-unsigned.ipa` must be signed before installation. Its identity is `app.telegaultra.client`, displayed as ULTRA. A new installation without App Groups can explicitly choose local storage, fully close the application and reopen it. Widgets and extensions cannot share the local database; push notifications need separate compatible provisioning and APNs configuration. Existing shared storage is never silently replaced with a new local database by this patch.

## Privacy boundary

ULTRA has its own settings block below the profile. **ULTRA → Диагностика** provides an opt-in local event journal, file export, clearing, and access to existing iOS crash reports. The journal records a closed list of technical events, never free-form messages, account identifiers or credentials. It retains at most 500 events for three days, with a 64 KiB file limit; expiry is enforced at the next journal access or launch. Recording is off by default. Disabling it retains existing events until expiry or clearing. Temporary share files are removed when sharing finishes or the app next launches; copies saved by the user remain under the user's control.

Crash reports are separate from the ULTRA journal. Their explicit export contains iOS/device metadata and stack information, with a confirmation before opening the system share sheet. iOS can deliver these reports late and does not report every termination. No automatic upload is added. The existing crash-report screen also offers its own reviewed, user-confirmed sending actions.

Telegram API parameters are embedded in compiled applications. Anyone receiving a decrypted IPA may extract them. Keeping them in Actions Secrets protects source files and CI configuration; encrypting published artifacts prevents public downloads from exposing the embedded values. Do not publish decrypted binaries, private identities, generated build configuration, signing material or account/session data.

## Upstream

[TelegramMessenger/Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS), pinned revision `24638bc69bd083981b178dd1e7f921eebbf7fc46` (13.2). Existing upstream copyright and license terms remain applicable to the inherited code and dependencies. This repository does not relicense upstream code. ULTRA is not an official Telegram product.
