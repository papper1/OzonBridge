# Windows Packaging

## Goal

Build one installer `.exe` that contains:

- Flutter desktop frontend
- Python backend executable
- Playwright Chromium runtime
- Seed templates and workbook assets

The installed app writes runtime data to:

- `%LOCALAPPDATA%\CrawlDesk Pro`

## Prerequisites

- Flutter SDK
- Python with access to `pip`
- Inno Setup 6

## One-command installer build

```powershell
cd "c:\Users\thang\OneDrive\Máy tính\tool mmo v2\packaging\windows"
.\preflight.ps1
.\build-installer.ps1
```

Output installer:

- `packaging\windows\output\installer\CrawlDeskProSetup.exe`

## Separate steps

Build backend runtime:

```powershell
.\build-backend.ps1
```

Build frontend release:

```powershell
.\build-frontend.ps1
```

## Unicode path note

If your repo lives under a Windows path containing Vietnamese characters such as `Máy tính`, the frontend build script now copies the Flutter project to:

- `C:\CrawlDeskBuild\frontend\crawldesk_pro`

and builds from there to avoid `app.dill` / Windows build failures caused by non-ASCII paths.

## Runtime layout inside the installed app

- `{app}\crawldesk_pro.exe`
- `{app}\runtime\backend\crawldesk_backend.exe`
- `{app}\runtime\ms-playwright\...`
- `{app}\runtime\templates\...`
- `{app}\runtime\assets\templates\...`

## Notes

- Backend is auto-started by Flutter on app launch.
- User-editable templates and crawl data are copied to `%LOCALAPPDATA%\CrawlDesk Pro` on first run.
- This layout is intentionally `installer exe -> installed folder`, not a fake single portable exe. It is more stable on other Windows machines.
