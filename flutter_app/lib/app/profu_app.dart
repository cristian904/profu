import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "package:supabase_flutter/supabase_flutter.dart";

import "../core/di/app_dependencies.dart";
import "../core/di/app_scope.dart";
import "../core/navigation/app_nav.dart";
import "../pages/login_page.dart";
import "../theme/app_theme.dart";
import "landing_page.dart";

void _authLog(String msg) {
  if (kDebugMode) {
    debugPrint("[AUTH_DEBUG] $msg");
  }
}

/// Root widget: provides [AppScope] and [MaterialApp] routes.
class ProfuApp extends StatefulWidget {
  /// Creates the app with pre-built [dependencies] from [bootstrapProfuApp].
  const ProfuApp({super.key, required this.dependencies});

  /// Injectable services (HTTP, Supabase, repositories).
  final AppDependencies dependencies;

  @override
  State<ProfuApp> createState() => _ProfuAppState();
}

class _ProfuAppState extends State<ProfuApp> {
  @override
  void initState() {
    super.initState();
    widget.dependencies.supabase.auth.onAuthStateChange.listen((AuthState data) {
      _authLog("onAuthStateChange: ${data.event} (session=${data.session != null})");
      void navigate() {
        final String target = data.event == AuthChangeEvent.signedIn ? "/" : "/login";
        final NavigatorState? state = appNavigatorKey.currentState;
        _authLog("navigate() target=$target currentState=${state != null}");
        if (state == null) {
          _authLog("navigate() SKIP: navigator currentState is null");
          return;
        }
        state.pushNamedAndRemoveUntil(target, (Route<dynamic> route) => false);
        _authLog("navigate() pushNamedAndRemoveUntil done");
      }

      if (data.event == AuthChangeEvent.signedIn) {
        WidgetsBinding.instance.addPostFrameCallback((_) => navigate());
      } else if (data.event == AuthChangeEvent.signedOut) {
        navigate();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      dependencies: widget.dependencies,
      child: MaterialApp(
        navigatorKey: appNavigatorKey,
        title: "Profu",
        theme: appLightTheme,
        darkTheme: appDarkTheme,
        themeMode: ThemeMode.dark,
        initialRoute: "/",
        routes: <String, WidgetBuilder>{
          "/": (BuildContext context) {
            final bool hasSession =
                widget.dependencies.supabase.auth.currentSession != null;
            _authLog("route '/' build: hasSession=$hasSession");
            return hasSession
                ? LandingPage(dependencies: widget.dependencies)
                : const LoginPage();
          },
          "/login": (BuildContext context) => const LoginPage(),
        },
      ),
    );
  }
}
