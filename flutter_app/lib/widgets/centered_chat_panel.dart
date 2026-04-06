import "package:flutter/material.dart";

/// Centers chat content with a max reading width. No frame or borders.
class CenteredChatLayout extends StatelessWidget {
  /// Wraps [child] (typically the chat [Column]) in a centered, width-capped area.
  const CenteredChatLayout({
    super.key,
    required this.child,
    this.maxContentWidth = 704,
    this.horizontalPadding = 20,
  });

  /// Message list + composer.
  final Widget child;

  /// Maximum width of the chat column (10% above former 640px cap).
  final double maxContentWidth;

  /// Horizontal inset from the pane edges (beside the conversations rail).
  final double horizontalPadding;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: horizontalPadding, vertical: 8),
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxContentWidth),
          child: child,
        ),
      ),
    );
  }
}
