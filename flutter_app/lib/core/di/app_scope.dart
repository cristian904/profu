import "package:flutter/material.dart";

import "app_dependencies.dart";

/// Provides [AppDependencies] to the widget tree below [MaterialApp].
class AppScope extends InheritedWidget {
  /// Wraps [child] with access to [dependencies].
  const AppScope({
    super.key,
    required this.dependencies,
    required super.child,
  });

  /// Shared services for the running app.
  final AppDependencies dependencies;

  /// Reads dependencies from the nearest [AppScope].
  static AppDependencies of(BuildContext context) {
    final AppScope? scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, "AppScope not found in context");
    return scope!.dependencies;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) {
    return dependencies != oldWidget.dependencies;
  }
}
