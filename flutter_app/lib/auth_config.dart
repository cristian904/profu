/// Google OAuth Web client ID for "Sign in with Google" on web.
/// Set via build: --dart-define=GOOGLE_WEB_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
/// Or replace the default below. Use a real client ID from Google Cloud Console for sign-in to work.
const String googleWebClientId = String.fromEnvironment(
  'GOOGLE_WEB_CLIENT_ID',
  defaultValue: '818837641497-fctb8mmbsqt4jp9u0p2dl1jbiq6lhu0f.apps.googleusercontent.com',
);
