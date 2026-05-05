import 'package:flutter/material.dart';

import 'router.dart';
import 'theme.dart';

class CrawlDeskProApp extends StatelessWidget {
  const CrawlDeskProApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      debugShowCheckedModeBanner: false,
      title: 'CrawlDesk Pro',
      theme: buildAppTheme(),
      routerConfig: router,
    );
  }
}
