import "package:flutter/material.dart";

import "../theme/app_colors.dart";

/// Full-bleed background matching the static landing page night sky gradient.
/// Place behind scrollable content; does not apply blur (cheap on all platforms).
class ProfuSceneBackground extends StatelessWidget {
  /// Creates a scene background with the given [child] painted on top.
  const ProfuSceneBackground({
    super.key,
    required this.child,
  });

  /// Content stacked above the gradient.
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: <Widget>[
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: AppGradients.bodyScene,
            ),
          ),
        ),
        child,
      ],
    );
  }
}
