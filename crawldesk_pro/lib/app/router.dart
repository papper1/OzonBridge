import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/widgets/app_shell.dart';
import '../features/crawl/crawl_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/results/result_screen.dart';
import '../features/settings/settings_screen.dart';
import '../features/templates/template_screen.dart';

final GoRouter router = GoRouter(
  initialLocation: '/',
  routes: <RouteBase>[
    ShellRoute(
      builder: (BuildContext context, GoRouterState state, Widget child) {
        return AppShell(child: child);
      },
      routes: <RouteBase>[
        GoRoute(
          path: '/',
          pageBuilder: (context, state) =>
              const NoTransitionPage<void>(child: DashboardScreen()),
        ),
        GoRoute(
          path: '/crawl',
          pageBuilder: (context, state) =>
              const NoTransitionPage<void>(child: CrawlScreen()),
        ),
        GoRoute(
          path: '/templates',
          pageBuilder: (context, state) =>
              const NoTransitionPage<void>(child: TemplateScreen()),
        ),
        GoRoute(
          path: '/results',
          pageBuilder: (context, state) =>
              const NoTransitionPage<void>(child: ResultScreen()),
        ),
        GoRoute(
          path: '/settings',
          pageBuilder: (context, state) =>
              const NoTransitionPage<void>(child: SettingsScreen()),
        ),
      ],
    ),
  ],
);
