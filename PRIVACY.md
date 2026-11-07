# Publication boundaries

Public files are the audited source patch, pinned build configuration, helper scripts, encryption tests and the public artifact recipient. No private account history or personal diagnostic reports are included.

Private Telegram API values are supplied through Actions Secrets. The generated configuration remains inside the temporary runner. All build artifacts and detailed build logs are encrypted with age before upload; plaintext upload paths are not part of the workflow. Intermediate artifacts are decrypted only inside subsequent trusted jobs using a repository secret.

This protects against public readers of the repository and its artifacts. It does not protect against a compromised maintainer account, malicious changes to a trusted workflow, compromised build dependencies or someone who is given the decrypted IPA/private encryption identity. Build tools and dependencies remain pinned where supported; this is not a claim that every dependency has been audited.

The artifact helper tests successful byte-for-byte recovery, failure with another identity, ciphertext tampering, archive traversal rejection, refusal to overwrite local files and failure when the decryption secret is absent. Public log and artifact exposure must be checked after actual CI execution as well.
