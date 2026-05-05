import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:crawldesk_pro/app/app.dart';

void main() {
  testWidgets('renders app shell title', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1800, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const ProviderScope(child: CrawlDeskProApp()));
    await tester.pumpAndSettle();

    expect(find.text('CrawlDesk Pro'), findsWidgets);
    expect(find.textContaining('quan'), findsWidgets);
  });
}
