# ChangeOrder App

SDSU AI Club's ChangeOrder app helps field contractors document changes to contracted work, send them to the office for review, and request client approval.

This guide covers local development on **Windows with PowerShell and an iPhone running Expo Go**. The current scaffold runs an Expo/React Native frontend and a FastAPI backend, with a **Check backend** button to verify connectivity. Photo submission, office review, AI, and client approval are planned features.

See [SPECIFICATIONS.MD](SPECIFICATIONS.MD) for the proposed architecture, workflows, data models, and API design. PostgreSQL is part of that design; it is not required for the current health-check scaffold.

## 1. Install the tools

Skip tools that are already installed and pass the version checks below.

| Tool            | Installation                                                                                                                                                                                                                                                                   |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Git             | Install [Git for Windows](https://git-scm.com/download/win) to clone the repository.                                                                                                                                                                                           |
| Node.js and npm | Install **Node.js 24 LTS** using the [Windows installer](https://nodejs.org/en/download). Keep the npm and PATH options enabled; npm is included with Node.js.                                                                                                                 |
| Python          | Install **Python 3.12**, including pip and the Windows `py` command. For a new PC, install the [Python install manager](https://www.python.org/downloads/windows/), then run `pymanager install 3.12`. An existing Python 3.12 installation with the `py` launcher also works. |
| Expo Go         | Install **Expo Go** from the iPhone App Store. [Expo Go downloads](https://expo.dev/go).                                                                                                                                                                                       |
| Editor          | Use an editor such as [Visual Studio Code](https://code.visualstudio.com/).                                                                                                                                                                                                    |

Close and reopen PowerShell after installing the tools, then verify:

```powershell
git --version
node --version
npm --version
py -3.12 --version
py -3.12 -m pip --version
```

The working setup used Node.js `v24.18.0`, npm `11.16.0`, and Python `3.12.10`. These are reference versions, not exact patch-version requirements. The Windows install script specifically selects **Python 3.12** with `py -3.12`.

The project installs Expo CLI locally with its frontend dependencies. A global Expo CLI installation is not needed.

## 2. Get the project

In PowerShell, navigate to the parent folder where you keep your projects, then run:

```powershell
git clone https://github.com/Avensky/ChangeOrder.git
cd ChangeOrder
```

If you already have the project, open its existing folder instead. Run the remaining commands from the **repository root**, which contains `package.json`, `scripts`, `backend`, and `frontend`.

### Prepare the environment templates

The installer expects `backend/.env.example` and `frontend/.env.example`. Some checkouts currently contain `env.example` without the leading dot. Run this once to supply the expected filenames when needed:

```powershell
if (!(Test-Path backend\.env.example)) {
    Copy-Item backend\env.example backend\.env.example
}
if (!(Test-Path frontend\.env.example)) {
    Copy-Item frontend\env.example frontend\.env.example
}
```

Keep the `.env.example` templates in version control so new contributors can run the installer.

## 3. Install the project dependencies

From the repository root:

```powershell
npm run install
```

This script:

1. Installs the root Node dependencies, including `concurrently`.
2. Installs the Expo/React Native frontend dependencies.
3. Creates `backend/.venv` using Python 3.12 if the virtual environment is missing.
4. Installs Python packages from `backend/requirements.txt` using the virtual environment's pip.
5. Copies the environment templates to `backend/.env` and `frontend/.env` if those local files do not exist.

Python's `venv` module includes pip by default. The scripts call the virtual environment's Python directly, so **activating the virtual environment is optional**. Re-running `npm run install` preserves existing `.env` files, including any old PC IP address stored there.

To confirm the backend environment is ready:

```powershell
.\backend\.venv\Scripts\python.exe --version
.\backend\.venv\Scripts\python.exe -m pip --version
```

## 4. Set the backend address for your phone

Connect the PC and iPhone to the **same local network**. In PowerShell, run:

```powershell
ipconfig
```

Find the **IPv4 Address** under the adapter connected to that network: usually Wi-Fi, or Ethernet if the PC is wired to the same router. Use that address rather than a VPN or virtual adapter address.

Open `frontend/.env` and set the PC address. For example, if `ipconfig` shows `192.168.1.50`:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.50:8000
```

Replace the example IP with **your PC's current IPv4 address**. Do not append `/health`; the test function adds it. On a physical phone, `localhost` and `127.0.0.1` refer to the phone. `0.0.0.0` is the backend's listen address, not a destination to put in the app.

**The PC IP can change** after reconnecting or switching networks. If the backend check starts timing out, check `ipconfig` again, update this value, and fully reload the app. Re-running the install script does not update the IP automatically.

The default `backend/.env` contains the browser origins allowed to call the API:

```dotenv
CORS_ORIGINS=http://localhost:8081,http://127.0.0.1:8081
```

These defaults support the local web preview. If you open the web preview through another origin, add that exact origin to the comma-separated list and restart the backend. Native Expo Go requests do not use browser CORS rules.

`EXPO_PUBLIC_` values are included in the frontend bundle. Use them for public configuration such as the API URL; keep private API keys in the backend.

## 5. Start development

From the repository root:

```powershell
npm run dev
```

This starts FastAPI on port **8000** and Expo/Metro on port **8081** using LAN mode. Keep the terminal running while testing. Press **Ctrl+C** to stop the development processes.

The root `package.json` should use this `dev` entry so Expo can display its QR code and interactive controls:

```json
"dev": "concurrently --raw --kill-others \"npm:dev:backend\" \"npm:dev:frontend\""
```

That line belongs inside the existing `scripts` object. Preserve the comma if another entry follows it.

### Open the app on iPhone

1. Scan the terminal QR code with the iPhone **Camera** app and open the link in **Expo Go**.
2. Allow Expo Go access to the local network if prompted. You can check this under **Settings > Privacy & Security > Local Network > Expo Go**.
3. On the app's Home screen, check the address shown in **Backend connection**, then tap **Check backend**.
4. A successful connection displays **Backend: ok**.

If Expo Go asks you to sign in, use the same Expo account on the phone and in Expo CLI. To sign in on the PC:

```powershell
Push-Location frontend
npx expo login
Pop-Location
```

If the phone shows an older screen, fully close Expo Go, reopen it, and scan the current QR code. After changing `frontend/.env`, perform a full reload using Expo Go's developer menu; Fast Refresh alone may leave the previous value visible.

## 6. Verify the backend directly

With the servers running, open these on the PC:

- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Frontend web preview: [http://localhost:8081](http://localhost:8081)

The health endpoint returns:

```json
{ "status": "ok" }
```

On the iPhone, open **the exact address displayed in the app**, followed by `/health`, in Safari. For the example IP above, that would be `http://192.168.1.50:8000/health`.

The Expo QR code connects to Metro on port 8081. The **Check backend** button makes a separate request to FastAPI on port 8000, so loading the frontend does not verify the API connection.

## Everyday commands

Run these from the repository root:

| Command                | Purpose                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `npm run install`      | Install root/frontend packages, create the backend virtual environment if missing, and install Python requirements. |
| `npm run dev`          | Start the backend and frontend together.                                                                            |
| `npm run dev:backend`  | Start only FastAPI, with reload enabled.                                                                            |
| `npm run dev:frontend` | Start only Expo in LAN mode and display its QR code.                                                                |
| `npm run typecheck`    | Check frontend TypeScript types.                                                                                    |
| `npm run lint`         | Run the frontend linter.                                                                                            |

On a normal workday, open the project, confirm the PC IP in `frontend/.env`, run `npm run dev`, and open the project in Expo Go. Re-run installation after dependency files change.

To add a frontend library, run `npx expo install PACKAGE_NAME` from `frontend` so Expo can select a compatible version. Add backend dependencies to `backend/requirements.txt`, then re-run the root installer.

## Troubleshooting

| Symptom                                                 | What to check                                                                                                                                                                         |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `node`, `npm`, `git`, or `py` is not recognized         | Reopen PowerShell after installing the tool and check its PATH configuration.                                                                                                         |
| PowerShell blocks `npm.ps1`                             | Use `npm.cmd run install` or `npm.cmd run dev` in place of the corresponding `npm` command.                                                                                           |
| Python 3.12 is not found                                | Check `py -3.12 --version`; the Windows installer script requires that version.                                                                                                       |
| Installer reports a missing `.env.example` file         | Run the template preparation commands in step 2, then re-run `npm run install`.                                                                                                       |
| Expo does not show a QR code                            | Confirm the root `dev` script includes `--raw`. You can also stop it and use `npm run dev:backend` and `npm run dev:frontend` in separate terminals.                                  |
| Phone shows the previous UI                             | Fully close Expo Go and scan the QR code from the current server.                                                                                                                     |
| `Connection timed out`                                  | Check the PC's current IPv4 address, the address displayed in the app, the running backend, and the shared local network. Update `frontend/.env` and fully reload after an IP change. |
| PC health check works, but iPhone Safari cannot open it | Check the LAN address and network first, then Windows Firewall access for the backend Python executable on your trusted private network.                                              |
| iPhone Safari health check works, but Expo Go fails     | Check Expo Go's Local Network permission and confirm the app displays the same API address. Fully reload after changing `.env`.                                                       |

## Manual backend setup (optional)

These commands show what the automated setup does for the backend. Use them for troubleshooting or when working on the backend alone; they are **not an additional required step** after a successful `npm run install`.

From the repository root:

```powershell
py -3.12 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install --upgrade pip
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

If pip is missing from the virtual environment, bootstrap it with:

```powershell
.\backend\.venv\Scripts\python.exe -m ensurepip --upgrade
```

Then repeat the pip installation commands above. Use `npm run dev:backend` to start the API; the launcher handles its working directory, `.env`, LAN binding, and reload options.

## Optional: Android Emulator on Windows

You can develop with your physical iPhone without installing an emulator. To also test Android:

1. Follow the [Expo Android Emulator setup guide](https://docs.expo.dev/workflow/android-studio-emulator/) to install Android Studio, its SDK tools, and configure `ANDROID_HOME` and the platform-tools PATH.
2. In Android Studio's **Device Manager**, create a virtual phone, install a system image, and start it.
3. Run `npm run dev`, then press **a** in the Expo terminal to open the project on the emulator. If terminal input is unreliable, run the frontend and backend in separate terminals using the commands above.
4. Test **Check backend** there as well. The API URL must be reachable from the emulator; verify the displayed URL in its browser if needed.

The local **iOS Simulator requires macOS and Xcode**. On this Windows setup, use your physical iPhone for local iOS testing. See [Expo's iOS Simulator guide](https://docs.expo.dev/workflow/ios-simulator/).

## Project layout and design

| Location                                          | Responsibility                                                                                               |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `scripts/`                                        | Shared installation and development launchers.                                                               |
| `backend/main.py`                                 | FastAPI entry point.                                                                                         |
| `backend/api/routes/`                             | HTTP routes, including `/health`.                                                                            |
| `backend/schemas/`                                | Request and response schemas.                                                                                |
| `backend/core/`                                   | Backend configuration.                                                                                       |
| `backend/services/`, `backend/ai/`, `backend/db/` | Starting locations for business logic, AI integrations, and database code as those features are implemented. |
| `frontend/src/app/`                               | Expo Router screens and layouts.                                                                             |
| `frontend/src/components/`                        | Reusable UI components.                                                                                      |
| `frontend/src/lib/api.ts`                         | Backend URL and health-check request.                                                                        |

Architecture and approval-flow details are in [SPECIFICATIONS.MD](SPECIFICATIONS.MD). This README focuses on getting the current development scaffold running.

## Collaborators

### SDSU AI Club members

- Aadi Bery (sdsuaiclub@gmail.com)
- Jaylan Luong (jluong5067@sdsu.edu)
- Uriel Zacarias (urielzacarias@gmail.com)
- Tad Schiller (tad@zacksmithplumbing.com)
- Ajay (arao3465@sdsu.edu)
- Bona O'Quinn (boquinn1053@sdsu.edu)

## Setup references

- [Node.js and npm installation](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm/)
- [Python on Windows](https://docs.python.org/3/using/windows.html)
- [Python virtual environments and pip](https://docs.python.org/3.12/library/venv.html)
- [Expo: start developing](https://docs.expo.dev/get-started/start-developing/)
- [Expo environment variables and reloading](https://docs.expo.dev/guides/environment-variables/)
