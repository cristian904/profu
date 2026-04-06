import "package:flutter/material.dart";

import "../models/conversation_models.dart";
import "../services/conversation_repository_api.dart";
import "conversation_sidebar.dart";

/// Conversation list with expand/collapse; collapsed state shows a narrow rail.
class CollapsibleConversationSidebar extends StatefulWidget {
  /// Creates a collapsible wrapper around [ConversationSidebar] parameters.
  const CollapsibleConversationSidebar({
    super.key,
    required this.type,
    required this.selectedConversation,
    required this.onConversationSelected,
    this.repository,
    this.expandedWidth = 300,
    this.collapsedWidth = 52,
  });

  final ConversationType type;
  final Conversation? selectedConversation;
  final ValueChanged<Conversation?> onConversationSelected;
  final ConversationRepositoryApi? repository;

  /// Width when the list is visible.
  final double expandedWidth;

  /// Width of the collapsed rail (icon only).
  final double collapsedWidth;

  @override
  State<CollapsibleConversationSidebar> createState() =>
      _CollapsibleConversationSidebarState();
}

class _CollapsibleConversationSidebarState
    extends State<CollapsibleConversationSidebar> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme scheme = theme.colorScheme;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeInOutCubic,
      width: _expanded ? widget.expandedWidth : widget.collapsedWidth,
      clipBehavior: Clip.hardEdge,
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(
          alpha: theme.brightness == Brightness.dark ? 0.28 : 0.65,
        ),
      ),
      child: _expanded
          ? Stack(
              clipBehavior: Clip.none,
              children: <Widget>[
                Positioned.fill(
                  child: Padding(
                    padding: const EdgeInsets.only(left: 40),
                    child: ConversationSidebar(
                      type: widget.type,
                      selectedConversation: widget.selectedConversation,
                      onConversationSelected: widget.onConversationSelected,
                      repository: widget.repository,
                    ),
                  ),
                ),
                Positioned(
                  top: 4,
                  left: 0,
                  child: IconButton(
                    visualDensity: VisualDensity.compact,
                    tooltip: "Ascunde conversațiile",
                    icon: Icon(
                      Icons.chevron_left,
                      color: scheme.onSurface.withValues(alpha: 0.85),
                    ),
                    onPressed: () {
                      setState(() {
                        _expanded = false;
                      });
                    },
                  ),
                ),
              ],
            )
          : Tooltip(
              message: "Arată conversațiile",
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () {
                    setState(() {
                      _expanded = true;
                    });
                  },
                  child: Center(
                    child: Icon(
                      Icons.forum_outlined,
                      size: 26,
                      color: scheme.primary.withValues(alpha: 0.95),
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}
