# GC review on a phone (U4)

The GC opens `/approve?token=…` in a browser, without signing in. Opening or reloading only reads the proposal. Approve/Decline opens a confirmation; only the confirmation sends a decision.

## Local demo setup

1. Put the demo PC and phone on the same Wi-Fi or hotspot. Guest networks may block device-to-device traffic.
2. Use the PC's LAN address (shown by `ipconfig` on Windows). In local `frontend/.env`, set `EXPO_PUBLIC_API_URL=http://<PC-LAN-IP>:8000`.
3. Start the backend so it listens on the LAN (`0.0.0.0:8000`), and allow its port through the local firewall. Jalen owns backend configuration.
4. Start Expo web from `frontend/`: `npm run web -- --lan`. Open `http://<PC-LAN-IP>:8081` on the phone. Expo Go is not needed for the external GC page.
5. Set the backend's local `APP_URL=http://<PC-LAN-IP>:8081` and restart it before the estimator sends a new proposal. Jalen owns this setting. Old emails retain their old address; generate a new link. Never write the token into a document or PR.
6. Open the emailed link or private console fallback on the phone. A link beginning with `localhost` points at the phone itself and must be regenerated with the correct APP_URL.

For web only, if the compiled API URL uses localhost/127.0.0.1 and the page opens on a LAN host, the frontend uses the page's host with the configured API port. Explicit remote API URLs are preserved. Native builds still require EXPO_PUBLIC_API_URL. This fallback does not change the address in an email.

For an off-network GC, use a reachable HTTPS frontend and HTTPS API, configure EXPO_PUBLIC_API_URL and APP_URL to those addresses, and allow the frontend origin in backend CORS. A LAN address works only on the same network. Hosting and backend configuration are outside Uriel's frontend task.

## Device checklist

- Open the page in a private phone browser with no staff session.
- Check the exact scope, currency/cost, calendar days and photos.
- Reload and verify the status is unchanged.
- Press Approve, then Keep reviewing; status must remain unchanged.
- Confirm approval and verify one saved decision; repeat with a separate proposal for decline.
- Open an invalid/expired/replaced link and verify there are no decision buttons.
- Test loss of connectivity: reload the proposal after an uncertain result before trying again.

Physical phone/network and real email delivery must be verified on the demo network. Automated browser checks do not establish external reachability.
