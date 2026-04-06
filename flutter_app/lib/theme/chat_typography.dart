import 'package:flutter/material.dart';

/// Font sizes for in-app chat (markdown, bubbles, hints). Slightly below default
/// body for denser reading.
abstract final class ChatTypography {
  ChatTypography._();

  /// User and assistant paragraph text.
  static const double body = 13;

  /// Inline / block code in markdown.
  static const double code = 12;

  static const double h1 = 20;
  static const double h2 = 17;
  static const double h3 = 15;

  /// List markers and tight body.
  static const double listBullet = 13;

  /// Composer [TextField].
  static const double input = 13;

  /// Max width for a single bubble inside the centered chat column (matches layout +10%).
  static const double bubbleMaxWidth = 572;
}

/// Borderless composer field; transparent fill so it floats on the scene like AI text.
InputDecoration chatComposerInputDecoration(
  BuildContext context, {
  required String hintText,
}) {
  final ColorScheme scheme = Theme.of(context).colorScheme;
  final OutlineInputBorder border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(24),
    borderSide: BorderSide.none,
  );
  return InputDecoration(
    hintText: hintText,
    hintStyle: TextStyle(color: scheme.onSurfaceVariant.withValues(alpha: 0.85)),
    filled: true,
    fillColor: Colors.transparent,
    border: border,
    enabledBorder: border,
    focusedBorder: border,
    errorBorder: border,
    focusedErrorBorder: border,
    disabledBorder: border,
    contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
  );
}
