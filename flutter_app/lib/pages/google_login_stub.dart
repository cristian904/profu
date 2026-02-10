import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';

/// Mobile: no stream setup; button triggers onTap (signIn() returns idToken).
void setupGoogleSignInListener(
  GoogleSignIn googleSignIn,
  void Function(String idToken) onIdToken,
) {}

Widget buildGoogleButton([VoidCallback? onTap]) {
  return OutlinedButton.icon(
    onPressed: onTap,
    icon: const Icon(Icons.g_mobiledata, size: 24),
    label: const Text('Continuă cu Google'),
  );
}
