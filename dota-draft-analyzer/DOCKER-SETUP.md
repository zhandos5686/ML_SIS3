# Docker: remaining system prerequisite

The project is ready for an actual container check. At the last inspection Docker Desktop was absent, and `wsl --status` returned exit code 50 with the Windows message that WSL was not installed. No successful Docker build or container run is claimed.

## One-time Windows setup

1. Open PowerShell **as Administrator** and run:

```powershell
wsl --install --no-distribution
```

Restart Windows if requested. This enables WSL without installing an extra Ubuntu distribution. If the command asks for administrator permission, approve it yourself. Do not turn off Windows security protections.

2. Install [Docker Desktop from the official Docker website](https://docs.docker.com/desktop/setup/install/windows-install/), select the WSL 2 backend, and open Docker Desktop. Read and accept its agreement yourself if you agree. Wait until the Linux engine is running. Initial WSL setup, reboot and acceptance of the agreement require your participation.

References: [Microsoft WSL commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands), [Docker Windows installation](https://docs.docker.com/desktop/setup/install/windows-install/).

## Finish all project checks

From this project folder in a normal PowerShell:

```powershell
.\verify-docker.ps1
```

If your PowerShell policy blocks local scripts, keep the policy unchanged and ask Codex to execute the reviewed script. The script does not install applications, alter Windows features, accept license terms, or delete files.

It builds the image, trains both models in Linux containers, starts services, checks the API and Swagger, checks Streamlit and MLflow HTTP responses, executes the complete pytest suite inside the API container, executes Streamlit AppTest with a real request to the API container, and verifies both models in MLflow Registry. It reports PASSED only after all commands succeed.

Container state is isolated under docker-state/ so native Windows models and MLflow history stay intact. Test ports are 18000 (API), 18501 (UI), 15000 (MLflow), so they do not conflict with native services on 8000/8501/5000. Containers remain running after the check.

Each invocation writes a fresh docker-evidence/<timestamp>/result.json and docker.log. A BLOCKED or FAILED report is not proof of success. Only a PASSED report, actual container screenshots and command logs may be used as Docker evidence for submission. Keep docker-state/ and its database out of Git; select only necessary evidence logs/screenshots for submission.
