---
id: IDEA-323
title: 'doctor: no false failure with env credentials, without a keychain or a project'
created: '2026-10-21T06:49:20+00:00'
source_project: dataio
source_path: /Users/bolandau/Work/tools/dataio
status: dropped
for_path: /Users/bolandau/Work/tools/dataio
reason: taken as task DATAIO-034 (bugfix, needs Acceptance, so task-create)
---

Bug from sysadmin (2026-10-21, dataio 0.1.28 on homeserver, user rbtools): DATAIO_GOOGLE_* are set and 'dataio auth status' reports google env/unchecked (ok), but 'dataio doctor' says healthy=false: credential_store fails without an OS keychain, 'credential' checks a provider 'default' that does not exist (dataio's provider is google), and 'project' fails outside a project although dataio works without one. Windmill runs 'dataio doctor' through rb-run, so agents read a false failure. Same code in template v1.25.8 (credentials/health.py doctor_checks). Expected: doctor's credential checks follow auth status (required providers ok or unchecked; the keychain is only a dev override), and no project is not a failure.
