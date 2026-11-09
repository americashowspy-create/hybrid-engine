# Security and scope

The built-in scanner is a static, **heuristic** signal generator. It is not a pentest, a complete SAST engine, a dependency audit or an RLS policy validator.

Findings point to path and line, never secret value. The tool avoids symbolic links, generated directories and large/binary files. A clean report **does not** prove safety.

Supabase public/publishable/legacy anon keys are not, by themselves, leaked secrets. Service-role/secret keys are privileged and must stay server-side. RLS must be verified from actual policies and live access tests; never infer its correctness from a single file.

## Hard stops

- Do not send repository contents, credentials, connection strings or exploitation steps to third parties by default.
- No active scanning against a remote service without explicit permission and constraints.
- No unreviewed changes to authentication, authorization, migrations or secrets.
- For serious security issues, use private disclosure; do not open public issues with exploit details.
- Existing project test scripts can have side effects. Run only with explicit `--tests` and review them first.

For deeper checks, integrate pinned external analyzers through separate reviewed CI jobs.
