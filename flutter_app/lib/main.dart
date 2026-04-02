import "package:flutter/material.dart";

import "app/bootstrap.dart";
import "app/profu_app.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final dependencies = await bootstrapProfuApp();
  runApp(ProfuApp(dependencies: dependencies));
}
