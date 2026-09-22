# External timestamp anchors

This directory holds independently verifiable proof that the capture files in
this repository existed, in exactly their current form, no later than the
anchor dates recorded here. A self-asserted timestamp proves nothing against
a motivated opponent; these anchors are attestations by parties outside this
project's control, obtained at anchor time and impossible to backdate.

What one run of `python3 tools/anchor.py run` produces:

1. **A manifest** (`manifests/<id>.txt`): the SHA-256 of every file under the
   paths listed in `tools/anchor-paths.txt`.
2. **A chain entry** (`entries/<id>.json`, mirrored as a line in
   `chain.jsonl`): the manifest hash plus the hash of the previous entry.
   The chain is append-only; altering any past entry or manifest breaks
   every later link.
3. **Two RFC 3161 timestamp tokens** (`tsa/<id>-freetsa.tsr`,
   `tsa/<id>-digicert.tsr`): CA-signed attestations that the entry hash
   existed at the stated time. Because the entry hash covers the manifest
   and the chain link, one token binds the full content and its position
   in the history.
4. **An OpenTimestamps proof** (`ots/<id>.json.ots`): the same entry file
   committed to the Bitcoin blockchain via public calendar servers. Proofs
   are pending for roughly a day after stamping; `python3 tools/anchor.py
   upgrade` collects the completed Bitcoin attestation. This proof remains
   verifiable even if every timestamp authority disappears.

The two mechanisms fail differently, which is why both are used: the RFC 3161
tokens are legible to courts and opposing counsel today; the OTS proof does
not depend on any company's continued existence or certificate hygiene.

## Independent verification (no trust in this project required)

Anyone can check a claim of the form "file F existed by date D":

1. Hash the file: `shasum -a 256 F` and find that hash in the manifest for
   an anchor run at or before D.
2. Hash the manifest file and confirm it matches `manifest_sha256` in that
   run's entry; recompute the entry hash
   (SHA-256 of the canonical JSON of the `entry` object) and confirm it
   matches `entry_sha256` and the chain links.
3. Verify a token against the entry hash:
   `openssl ts -verify -digest <entry_sha256> -in tsa/<id>-freetsa.tsr
   -CAfile tsa/certs/freetsa-cacert.pem`
   (for the DigiCert token, use the system CA bundle as `-CAfile`).
4. Or verify the Bitcoin proof: `ots verify ots/<id>.json.ots`
   (requires the OpenTimestamps client; `pip install opentimestamps-client`).

`python3 tools/anchor.py verify` performs steps 2–3 for the entire chain.

## Routine

- Run `python3 tools/anchor.py run` after every capture session (or on the
  nightly review). Runs are cheap; unchanged files simply re-appear in the
  next manifest.
- Run `python3 tools/anchor.py upgrade` a day or more after any run.
- Commit `anchors/` with the captures it covers. Git history and the
  external anchors corroborate each other; neither replaces the other.
- Never edit anything under `anchors/`. Mistakes are superseded by later
  runs, not corrected in place.

## Scope note

The first entry in each chain is a backfill: it proves the then-existing
captures existed as of the backfill date, not as of their internal capture
dates. Every capture made after anchoring began carries a near-contemporaneous
external anchor, which is the standard this project maintains going forward.
The `ASSEMBLED`/`retrieved` dates inside packets, git history, and the
external anchors are three independent witnesses; their agreement is the
evidentiary claim.
