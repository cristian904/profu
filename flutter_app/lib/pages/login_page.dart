import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../core/navigation/app_nav.dart';
import '../auth_config.dart';
import 'google_login_stub.dart' if (dart.library.html) 'google_login_web.dart' as google_login;
import 'register_page.dart';

/// Login via email/password or Google. Navigates to home on success.
class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String? _error;
  late final GoogleSignIn _googleSignIn;

  @override
  void initState() {
    super.initState();
    _googleSignIn = GoogleSignIn(
      clientId: kIsWeb ? googleWebClientId : null,
      scopes: ['openid', 'email'],
    );
    if (!kIsWeb) {
      google_login.setupGoogleSignInListener(_googleSignIn, _onGoogleIdToken);
    }
  }

  /// Web only: redirect to Google via Supabase OAuth (no popup/GIS).
  Future<void> _signInWithGoogleWeb() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await Supabase.instance.client.auth.signInWithOAuth(
        OAuthProvider.google,
        redirectTo: Uri.base.origin + Uri.base.path,
      );
    } on AuthException catch (e) {
      if (mounted) {
        final msg = e.message;
        final isProviderDisabled = msg.contains('provider is not enabled') ||
            msg.contains('Unsupported provider');
        setState(() {
          _error = isProviderDisabled
              ? 'Google is not enabled in Supabase. Local (127.0.0.1:54321): edit supabase/config.toml — '
                'add [auth.external.google] with enabled=true, client_id, secret; then npx supabase stop && start. '
                'See docs/SUPABASE_GOOGLE_LOCAL.md.'
              : msg;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        final s = e.toString();
        final isProviderDisabled = s.contains('provider is not enabled') ||
            s.contains('Unsupported provider');
        setState(() {
          _error = isProviderDisabled
              ? 'Google is not enabled in Supabase. Local (127.0.0.1:54321): edit supabase/config.toml — '
                'add [auth.external.google] with enabled=true, client_id, secret; then npx supabase stop && start. '
                'See docs/SUPABASE_GOOGLE_LOCAL.md.'
              : s;
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _onGoogleIdToken(String idToken) async {
    if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken called, mounted=$mounted');
    if (!mounted) {
      if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken SKIP: !mounted');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken calling signInWithIdToken');
      await Supabase.instance.client.auth.signInWithIdToken(
        provider: OAuthProvider.google,
        idToken: idToken,
      );
      if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken signInWithIdToken done, mounted=$mounted');
      if (!mounted) {
        if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken SKIP nav: !mounted after signIn');
        return;
      }
      final navState = appNavigatorKey.currentState;
      if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken navState=${navState != null}');
      if (navState != null) {
        navState.pushNamedAndRemoveUntil('/', (route) => false);
        if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken pushNamedAndRemoveUntil done');
      } else {
        if (kDebugMode) debugPrint('[AUTH_DEBUG] _onGoogleIdToken SKIP nav: navState is null');
      }
    } on AuthException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _signInWithPassword() async {
    if (_formKey.currentState?.validate() != true) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await Supabase.instance.client.auth.signInWithPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/');
    } on AuthException catch (e) {
      setState(() {
        _error = e.message;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  /// Used on mobile only; web uses GIS renderButton + authenticationEvents.
  Future<void> _signInWithGoogle() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await _googleSignIn.signIn();
      if (response == null) {
        setState(() => _isLoading = false);
        return;
      }
      final googleAuth = await response.authentication;
      final idToken = googleAuth.idToken;
      if (idToken == null) {
        setState(() {
          _error = 'Google sign-in: no ID token';
          _isLoading = false;
        });
        return;
      }
      await _onGoogleIdToken(idToken);
    } on AuthException catch (e) {
      setState(() {
        _error = e.message;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Image.asset(
                    'imgs/gemini_gray.png',
                    height: 120,
                    fit: BoxFit.contain,
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Profu',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Autentificare',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withValues(alpha: 0.7),
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),
                  Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 280),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextFormField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            autocorrect: false,
                            style: const TextStyle(fontSize: 14),
                            decoration: InputDecoration(
                              labelText: 'Email',
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 10,
                              ),
                              border: OutlineInputBorder(
                                borderSide: BorderSide(
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderSide: BorderSide(
                                  color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.7),
                                ),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderSide: BorderSide(
                                  color: Theme.of(context).colorScheme.primary,
                                  width: 1.5,
                                ),
                              ),
                              prefixIcon: const Icon(Icons.email_outlined, size: 20),
                            ),
                            validator: (v) {
                              if (v == null || v.trim().isEmpty) {
                                return 'Introdu emailul';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _passwordController,
                            obscureText: true,
                            style: const TextStyle(fontSize: 14),
                            decoration: InputDecoration(
                              labelText: 'Parolă',
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 10,
                              ),
                              border: OutlineInputBorder(
                                borderSide: BorderSide(
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderSide: BorderSide(
                                  color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.7),
                                ),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderSide: BorderSide(
                                  color: Theme.of(context).colorScheme.primary,
                                  width: 1.5,
                                ),
                              ),
                              prefixIcon: const Icon(Icons.lock_outline, size: 20),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) {
                                return 'Introdu parola';
                              }
                              return null;
                            },
                          ),
                          if (_error != null) ...[
                            const SizedBox(height: 12),
                            Text(
                              _error!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                                fontSize: 13,
                              ),
                            ),
                          ],
                          const SizedBox(height: 20),
                          FilledButton(
                            onPressed: _isLoading ? null : _signInWithPassword,
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                            child: _isLoading
                                ? const SizedBox(
                                    height: 20,
                                    width: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Text('Autentificare'),
                          ),
                          const SizedBox(height: 12),
                          google_login.buildGoogleButton(
                            kIsWeb
                                ? (_isLoading ? null : _signInWithGoogleWeb)
                                : (_isLoading ? null : _signInWithGoogle),
                          ),
                          const SizedBox(height: 16),
                          TextButton(
                            onPressed: () {
                              Navigator.of(context).push(
                                MaterialPageRoute<void>(
                                  builder: (context) => const RegisterPage(),
                                ),
                              );
                            },
                            style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                            ),
                            child: const Text('Nu ai cont? Creează unul'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
