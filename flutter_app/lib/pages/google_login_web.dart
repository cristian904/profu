import 'package:flutter/material.dart';

/// Web: no GIS stream setup; we use Supabase OAuth redirect instead.
void setupGoogleSignInListener(
  dynamic googleSignIn,
  void Function(String idToken) onIdToken,
) {
  // No-op on web: Google sign-in uses signInWithOAuth (redirect), not idToken callback.
}

/// Web: plain button that triggers Supabase OAuth redirect (avoids GIS plugin bug).
Widget buildGoogleButton([VoidCallback? onTap]) {
  return OutlinedButton.icon(
    onPressed: onTap,
    icon: const Icon(Icons.login, size: 20),
    label: const Text('Sign in with Google'),
  );
}
