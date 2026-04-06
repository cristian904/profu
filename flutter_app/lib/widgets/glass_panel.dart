import "dart:ui";

import "package:flutter/material.dart";

import "../theme/app_colors.dart";

/// Frosted glass panel: blur + semi-transparent fill + landing-style border.
/// Blur cost is moderate on web; use a lower [blurSigma] if performance drops.
class GlassPanel extends StatelessWidget {
  /// Builds a glass panel around [child].
  const GlassPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(24),
    this.borderRadius = 18,
    this.blurSigma = 14,
    this.fillAlpha = 0.58,
  });

  /// Inner content.
  final Widget child;

  /// Insets inside the frosted layer.
  final EdgeInsetsGeometry padding;

  /// Corner radius (matches landing `--radius-lg`).
  final double borderRadius;

  /// Gaussian blur sigma for [BackdropFilter].
  final double blurSigma;

  /// Opacity for the tinted overlay above the blur (0–1).
  final double fillAlpha;

  @override
  Widget build(BuildContext context) {
    final BorderRadius radius = BorderRadius.circular(borderRadius);
    return ClipRRect(
      borderRadius: radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: radius,
            color: AppColors.slateDeep.withValues(alpha: fillAlpha),
            border: Border.all(color: AppColors.border),
          ),
          child: Padding(
            padding: padding,
            child: child,
          ),
        ),
      ),
    );
  }
}
