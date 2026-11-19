# Windows Auto-Start

PDF Toolkit v1.0.0 can be configured to start when the current Windows 10/11 user signs in. This optional Task Scheduler guide uses the project's Python virtual environment and Uvicorn; it does not require a new startup script, WSL2, Docker, Nginx, Apache, or a machine-wide PowerShell execution-policy change. Read the [installation instructions](../README.md#install-and-run) first. These steps have been reviewed against the source but **not run on Windows** during this documentation task.

The [planned repository](https://github.com/glitter-node/pdf-toolkit) is currently empty. No public GitHub release or release asset is available to download from it yet. Use a trusted copy of the project source containing `app\main.py` and `requirements.txt`.

## Prerequisites and initial installation

- Use Windows 10/11 and an installed Python 3.11 interpreter. The repository has no enforced `requires-python` minimum; Python 3.11.10 is the current Linux test environment, and native Windows package compatibility has not been verified here.
- Keep the project directory and virtual environment at stable paths. Use a normal current-user account and confirm port 8013 is free.
- The app uses PyMuPDF, pypdf, ReportLab, Pillow and cryptography via [requirements.txt](../requirements.txt). No FFmpeg or external PDF command is required by the source.
- Preserve any existing `.env`, `.venv`, and user PDF files. The app itself does not configure a persistent upload directory.

In a non-elevated PowerShell window, run from the intended project directory:

```powershell
Set-Location (Read-Host "Enter the full path to the PDF Toolkit project")
Test-Path .\app\main.py
Test-Path .\requirements.txt
py --list
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The two `Test-Path` results must be `True`. If `.venv` already exists, inspect and preserve it instead of replacing it. If `py -3.11` is unavailable, use an installed interpreter whose package wheels match Windows and the interpreter architecture. Package installation is a required step on the actual Windows PC and was not executed here.

## Verify a foreground start first

From the project root:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8013
```

Open `http://127.0.0.1:8013/` and check `http://127.0.0.1:8013/healthz`. A healthy endpoint returns `{"status":"ok"}`; it does not prove that PDF editing or downloads work. Try a small test PDF in the browser. Stop this foreground server with Ctrl+C before testing the scheduled task. No PowerShell activation script is required.

## Optional startup script

No Windows startup script is bundled. Task Scheduler can run `.venv\Scripts\python.exe` directly, avoiding an extra script and execution-policy changes. This direct launch does not automatically write stdout/stderr to a log file.

## Configure a current-user logon task

These are instructions only; this document does not register or start a task.

1. Open **Task Scheduler** and select **Create Task**. Name it `PDF Toolkit - Current User`.
2. On **General**, select the current user, **Run only when user is logged on**, and leave **Run with highest privileges** unchecked.
3. On **Triggers**, choose **At log on** for that user. This starts after sign-in, not at boot before sign-in.
4. On **Actions**, choose **Start a program**. Set **Program/script** to the absolute `<PROJECT_PATH>\.venv\Scripts\python.exe`, **Add arguments** to `-m uvicorn app.main:app --host 127.0.0.1 --port 8013`, and **Start in** to the absolute project-root directory without quotes. The working directory matters for optional `.env` loading.
5. On **Settings**, choose **Do not start a new instance** if already running and **Run task as soon as possible after a scheduled start is missed**. If wanted, retry a failed task every one minute up to three times. Remove any maximum execution time that would stop a long-lived local server.
6. Review the user, trigger, action, working directory and port before enabling or manually running the task.

The no-new-instance setting prevents duplicates of this task only. It cannot detect a separate manually started Uvicorn process. Use one server process for this local guide; the PDF concurrency limiter is per process.

### PowerShell registration alternative

This **unexecuted example** creates the same current-user task and refuses to replace one with the same name. Review every path and the port before running on the intended Windows PC:

```powershell
$projectRoot = (Resolve-Path (Read-Host "Enter the full path to the PDF Toolkit project")).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$taskName = "PDF Toolkit - Current User"
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw "Virtual environment Python not found: $pythonPath" }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "app\main.py") -PathType Leaf)) { throw "PDF Toolkit entry point not found" }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw "Task already exists: $taskName" }
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "-m uvicorn app.main:app --host 127.0.0.1 --port 8013" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType InteractiveToken -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Starts local PDF Toolkit at user logon."
```

The example does not open a firewall port, modify `.env`, launch a server, or publish it on the network. Change the argument and verification URLs together if using another port.

## Existing process and port conflicts

Before manual or scheduled startup, inspect port 8013:

```powershell
Get-NetTCPConnection -LocalPort 8013 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress, OwningProcess
```

For a reported process ID, replace `1234` in this read-only inspection:

```powershell
Get-CimInstance Win32_Process -Filter "ProcessId = 1234" | Select-Object ProcessId, ExecutablePath, CommandLine
```

Confirm the owner and command before stopping anything. Do not force-stop an unknown process. Task Scheduler's duplicate prevention does not resolve a port already occupied by another program.

## Logging, restart, and failure handling

Enable and inspect the task's **History** tab and Windows **Event Viewer → Applications and Services Logs → Microsoft → Windows → TaskScheduler → Operational**. Check the task's Last Run Result. Direct Python execution does not create a dedicated log file automatically. To diagnose an import or startup error, run the foreground command from the same directory and user account. A process restart loads changed source; do it only after checking active work and preserving data.

## Verify after Windows sign-in

1. Sign out and sign back in; check the task status and Last Run Result.
2. Confirm one listener on `127.0.0.1:8013` and request `/healthz` and `/`.
3. Load a small test PDF, inspect preview pages, process one safe operation and download its result.
4. Confirm the source and runtime version separately with `/openapi.json` if relevant.

## Stop, disable, re-enable, or remove

```powershell
Stop-ScheduledTask -TaskName "PDF Toolkit - Current User"
Disable-ScheduledTask -TaskName "PDF Toolkit - Current User"
Enable-ScheduledTask -TaskName "PDF Toolkit - Current User"
Unregister-ScheduledTask -TaskName "PDF Toolkit - Current User" -Confirm:$true
```

Stopping or deleting the scheduled task does not delete project files or user PDF documents. Review the task before running removal commands.

## Security and data preservation

Binding to `127.0.0.1` limits the listener to the same host. The FastAPI PDF API has no user authentication or rate limit, and the per-process concurrency limit is not CPU/memory/time isolation. Do not switch to a public bind or Internet reverse proxy without a deliberate access policy, TLS, request limits, timeouts and process resource isolation. Protect `.env`, the virtual environment, source PDFs and downloaded results. Never overwrite an existing project or user data directory just to recreate the scheduled task.

## Troubleshooting and limitations

- **Python missing:** use `py --list` and confirm the selected interpreter and architecture.
- **Dependency installation fails:** inspect the package and wheel error; Windows package compatibility was not verified in this documentation task.
- **Port conflict:** inspect the owner with the commands above; do not terminate unknown software.
- **Task does not start:** check its account, `Start in`, executable path, History, Last Run Result and Event Viewer.
- **Upload or save fails:** inspect PDF extension, signature, encryption, size, page count and app response; test a known-good small PDF.
- **Browser preview differs from output:** inspect the exported PDF in a reader. Browser E2E and Acrobat compatibility are not claimed by this guide.

See [README](../README.md) for API routes, configuration, security headers and development tests.
