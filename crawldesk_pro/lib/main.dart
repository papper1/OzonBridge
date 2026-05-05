import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'core/runtime/desktop_runtime.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await DesktopRuntime.instance.initialize();
  runApp(const ProviderScope(child: CrawlDeskProApp()));
}
