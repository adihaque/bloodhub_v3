# Blood Hub mobile app

Flutter client for donor and requester workflows. The app is intentionally compile-oriented and does not require the Flutter SDK to be present in this repository.

## Setup

1. Install Flutter (stable), then run `flutter pub get` and `flutter run` from this directory.
2. Configure the API URL with `--dart-define=API_BASE_URL=https://your-host.example.com` (default is `http://10.0.2.2:8000/api/v1` for Android emulator).
3. Add Firebase Android/iOS configuration (`google-services.json` and `GoogleService-Info.plist`) and enable Firebase Messaging. The app starts safely without Firebase files, but push delivery is disabled.
4. Add the platform permissions below before release:
   - Android: `INTERNET`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, `POST_NOTIFICATIONS`, and a notification channel/icon.
   - iOS: location usage descriptions, notification capability, background remote notifications, and APNs key in Firebase.

The client only calls existing API resources under `/api/v1/auth`, `/api/v1/donors`, and `/api/v1/requests`. Refresh token support accepts a server-provided `refresh_token` and calls `/auth/refresh`; if the backend does not expose that route yet, the access token is cleared on expiry. Offline mutations are queued in memory and replayed after connectivity returns; replace the queue store with durable encrypted persistence for production.
