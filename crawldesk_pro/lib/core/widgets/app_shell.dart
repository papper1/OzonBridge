import 'package:flutter/material.dart';

import '../constants/app_sizes.dart';
import 'app_sidebar.dart';
import 'app_top_bar.dart';

class AppShell extends StatelessWidget {
  const AppShell({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final collapsed = constraints.maxWidth < 1280;
        return Scaffold(
          body: Row(
            children: <Widget>[
              AppSidebar(collapsed: collapsed),
              Expanded(
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSizes.pagePadding),
                    child: Column(
                      children: <Widget>[
                        const AppTopBar(),
                        const SizedBox(height: AppSizes.sectionGap),
                        Expanded(child: child),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
