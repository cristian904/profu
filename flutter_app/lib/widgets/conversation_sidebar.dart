import 'package:flutter/material.dart';

import '../models/conversation_models.dart';
import '../services/conversation_repository.dart';

class ConversationSidebar extends StatefulWidget {
  final ConversationType type;
  final Conversation? selectedConversation;
  final ValueChanged<Conversation?> onConversationSelected;

  const ConversationSidebar({
    super.key,
    required this.type,
    required this.selectedConversation,
    required this.onConversationSelected,
  });

  @override
  State<ConversationSidebar> createState() => _ConversationSidebarState();
}

class _ConversationSidebarState extends State<ConversationSidebar> {
  final ConversationRepository _repository = ConversationRepository();

  late Future<List<Conversation>> _futureConversations;

  @override
  void initState() {
    super.initState();
    _futureConversations = _repository.listConversations(type: widget.type);
  }

  void _reload() {
    setState(() {
      _futureConversations = _repository.listConversations(type: widget.type);
    });
  }

  Future<void> _editTitle(BuildContext context, Conversation conversation) async {
    final controller = TextEditingController(
      // Prefer custom name when present; fall back to auto title.
      text: conversation.name ?? conversation.title ?? '',
    );

    final newTitle = await showDialog<String?>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Editează titlul conversației'),
          content: TextField(
            controller: controller,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Titlu',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(null),
              child: const Text('Anulează'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(controller.text.trim()),
              child: const Text('Salvează'),
            ),
          ],
        );
      },
    );

    if (newTitle == null) return;

    try {
      final updated = await _repository.updateConversationTitle(
        conversationId: conversation.id,
        // Empty string clears the custom name (handled in repository).
        title: newTitle,
      );

      // Update selected conversation in parent if needed
      if (widget.selectedConversation?.id == updated.id) {
        widget.onConversationSelected(updated);
      }

      _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Nu am putut salva titlul: $e')),
        );
      }
    }
  }

  Future<void> _deleteConversation(BuildContext context, Conversation conv) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Șterge conversația'),
          content: const Text(
            'Sigur că vrei să ștergi această conversație?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Anulează'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              style: TextButton.styleFrom(
                foregroundColor: Theme.of(context).colorScheme.error,
              ),
              child: const Text('Șterge'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) return;

    try {
      await _repository.deleteConversation(conversationId: conv.id);
      if (widget.selectedConversation?.id == conv.id) {
        widget.onConversationSelected(null);
      }
      _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Nu am putut șterge conversația: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Container(
      width: 260,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant.withOpacity(isDark ? 0.3 : 0.7),
        border: Border(
          right: BorderSide(
            color: theme.dividerColor.withOpacity(0.3),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 8, 8),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Conversații',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: _reload,
                  tooltip: 'Reîncarcă',
                  icon: const Icon(Icons.refresh, size: 20),
                ),
              ],
            ),
          ),
          Expanded(
            child: FutureBuilder<List<Conversation>>(
              future: _futureConversations,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        'Nu am putut încărca conversațiile.',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.error,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  );
                }
                final conversations = snapshot.data ?? [];
                if (conversations.isEmpty) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'Nu ai încă nicio conversație salvată.\nÎncepe o conversație nouă!',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.7),
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: conversations.length,
                  itemBuilder: (context, index) {
                    final conv = conversations[index];
                    final isSelected =
                        widget.selectedConversation?.id == conv.id;

                    final displayTitle = (conv.name?.trim().isNotEmpty ?? false)
                        ? conv.name!.trim()
                        : (conv.title?.trim().isNotEmpty ?? false)
                            ? conv.title!.trim()
                            : 'Conversație din ${_formatDate(conv.createdAt)}';

                    return ListTile(
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                      dense: true,
                      selected: isSelected,
                      selectedTileColor:
                          theme.colorScheme.primary.withOpacity(0.15),
                      title: Text(
                        displayTitle,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        _formatTime(conv.createdAt),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.edit, size: 18),
                            tooltip: 'Editează titlul',
                            onPressed: () => _editTitle(context, conv),
                          ),
                          IconButton(
                            icon: Icon(Icons.delete_outline, size: 18,
                                color: theme.colorScheme.error),
                            tooltip: 'Șterge conversația',
                            onPressed: () => _deleteConversation(context, conv),
                          ),
                        ],
                      ),
                      onTap: () => widget.onConversationSelected(conv),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime dt) {
    return '${dt.day.toString().padLeft(2, '0')}.${dt.month.toString().padLeft(2, '0')}.${dt.year}';
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

