import 'package:flutter/material.dart';

// Dark theme palette: mostly dark with dark cyan touches
const Color _darkBackground = Color(0xFF3B3B3B); // main page background
const Color _darkSurface = Color(0xFF1E1E1E);
const Color _darkCyanPrimary = Color(0xFF0D7377);
const Color _darkCyanSecondary = Color(0xFF14A3A3);
const Color _onPrimary = Color(0xFFE0F7F7);
const Color _onSurface = Color(0xFFE0E0E0);
const Color _outlineVariant = Color(0xFF2D3D3D); // subtle dark cyan tint

/// Dark theme: mostly dark with dark cyan as primary accent.
ThemeData get appDarkTheme {
  final colorScheme = ColorScheme.dark(
    primary: _darkCyanPrimary,
    onPrimary: _onPrimary,
    primaryContainer: _darkCyanPrimary.withOpacity(0.3),
    onPrimaryContainer: _onPrimary,
    secondary: _darkCyanSecondary,
    onSecondary: _onPrimary,
    surface: _darkSurface,
    onSurface: _onSurface,
    surfaceContainerHighest: const Color(0xFF2A2A2A),
    onSurfaceVariant: _onSurface.withOpacity(0.8),
    outline: _outlineVariant,
    outlineVariant: _outlineVariant.withOpacity(0.5),
    error: Colors.redAccent,
    onError: Colors.white,
    errorContainer: Colors.redAccent.withOpacity(0.2),
    onErrorContainer: Colors.redAccent,
    inversePrimary: _darkCyanSecondary,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: _darkBackground,
    cardTheme: CardThemeData(
      color: _darkSurface,
      elevation: 2,
    ),
    drawerTheme: const DrawerThemeData(
      backgroundColor: Colors.black,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.black,
      foregroundColor: _onSurface,
      iconTheme: const IconThemeData(color: _darkCyanSecondary),
    ),
    tabBarTheme: TabBarThemeData(
      labelColor: _onSurface,
      unselectedLabelColor: _onSurface.withOpacity(0.7),
      indicatorColor: _darkCyanSecondary,
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: const OutlineInputBorder(),
      focusedBorder: OutlineInputBorder(
        borderSide: BorderSide(color: _darkCyanSecondary.withOpacity(0.8)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: _darkCyanPrimary,
        foregroundColor: _onPrimary,
      ),
    ),
  );
}

/// Light theme (unchanged from original; for future theme switching).
ThemeData get appLightTheme {
  return ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: Colors.blue,
      brightness: Brightness.light,
    ),
    useMaterial3: true,
  );
}
