import "package:flutter/material.dart";

/// Design tokens aligned with [landing/css/style.css] (`:root` and `body` background).
/// Keep in sync when the marketing site palette changes.
abstract final class AppColors {
  AppColors._();

  /// `--color-bg`
  static const Color bg = Color(0xFF050816);

  /// `--color-bg-alt`
  static const Color bgAlt = Color(0xFF0B1020);

  /// `--color-surface`
  static const Color surface = Color(0xFF111827);

  /// `--color-surface-alt`
  static const Color surfaceAlt = Color(0xFF1F2937);

  /// `--color-primary`
  static const Color primary = Color(0xFF3B82F6);

  /// `--color-accent`
  static const Color accent = Color(0xFFF97316);

  /// `--color-text`
  static const Color text = Color(0xFFE5E7EB);

  /// `--color-text-muted`
  static const Color textMuted = Color(0xFF9CA3AF);

  /// `--color-primary-soft` (approximate solid for non-layered fills)
  static const Color primarySoft = Color(0x1F3B82F6);

  /// `--color-border` as ARGB (`rgba(156, 163, 175, 0.35)`)
  static const Color border = Color(0x599CA3AF);

  /// Deep slate used in landing cards / overlays
  static const Color slateDeep = Color(0xFF0F172A);

  /// `--shadow-soft` approximate base (for reference; Flutter uses elevation / borders)
  static const Color shadowSoft = Color(0xBF0F172A);
}

/// Gradients used across the glass shell (landing marketing patterns).
abstract final class AppGradients {
  AppGradients._();

  /// Approximates `body { background: radial-gradient(circle at top, #1e293b 0, #020617 50%, #000 100%); }`
  static const RadialGradient bodyScene = RadialGradient(
    center: Alignment(0, -0.85),
    radius: 1.35,
    colors: <Color>[
      Color(0xFF1E293B),
      Color(0xFF020617),
      Color(0xFF000000),
    ],
    stops: <double>[0.0, 0.5, 1.0],
  );

  /// Landing `.btn--primary` / hero CTA: `linear-gradient(90deg, var(--color-primary), var(--color-accent))`
  static const LinearGradient primaryCta = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: <Color>[
      AppColors.primary,
      AppColors.accent,
    ],
  );

  /// Subtle radial used on feature / pricing cards on the landing site
  static const RadialGradient cardGlow = RadialGradient(
    center: Alignment.topLeft,
    radius: 1.25,
    colors: <Color>[
      Color(0x2E3B82F6),
      AppColors.surface,
    ],
    stops: <double>[0.0, 1.0],
  );
}
