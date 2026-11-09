# ZULTIBALL AI – Android Auto-Sync Starter

A native Java Android starter with a black/neon-green dashboard and an official Zulti draw-page reader.

## What works
- Android dashboard UI.
- User can paste a public Zulti draw result page URL.
- The app opens that page in a hidden WebView and reads the visible "Winning numbers" section.
- Supports draws containing different counts of winning numbers (for example, 7 or 8).
- Refreshes the saved draw page every 6 hours while the app remains open.
- Stores the last successfully read result locally.

## Important limitations
- Zulti's public website pages and indexed draw pages were checked, but no documented public API/feed for discovering the newest draw was found.
- Therefore this build does **not** independently discover a brand-new latest draw. The user must paste the official result-page URL once; the app can then re-read that same page periodically.
- If Zulti changes its page structure, the reader may need updating.
- This is not a hack, MOD, or server bypass. It only reads a public result page.
- Lottery outcomes are random. Historical statistics cannot guarantee future results.

## Setup / build
1. Extract this ZIP.
2. Open the folder in Android Studio.
3. Sync Gradle.
4. Build > Build APK(s).

Package: `com.zultiball.predictor`

## How to use
1. Open the app.
2. Copy a public Zultiball result page URL from `https://zulti.com/draws/...`.
3. Paste it into the URL field and tap **SYNC OFFICIAL RESULT**.
4. The app displays the winning numbers if it can read the page.
5. The saved URL is refreshed every 6 hours while the app is running.

## Future improvement
For hands-free discovery of newly published draws, Zulti would need to provide a documented public API, RSS/feed, or stable public draw-list endpoint. Do not rely on undocumented/private endpoints or bypass access controls.
