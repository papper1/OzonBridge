import 'package:flutter/material.dart';

import '../../../core/widgets/app_card.dart';
import '../crawl_state.dart';

class CrawlConfigSummary extends StatelessWidget {
  const CrawlConfigSummary({required this.state, super.key});

  final CrawlState state;

  @override
  Widget build(BuildContext context) {
    final entries = <MapEntry<String, String>>[
      MapEntry<String, String>('Nguồn dữ liệu', state.source),
      MapEntry<String, String>('Số URL', '${state.inputCount}'),
      MapEntry<String, String>('Template', state.template),
      MapEntry<String, String>(
        'Dịch tiếng Nga',
        state.translateToRussian ? 'Bật' : 'Tắt',
      ),
      MapEntry<String, String>(
        'Export Excel',
        state.exportExcel ? 'Bật' : 'Tắt',
      ),
    ];

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Tóm tắt cấu hình',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          ...entries.map(
            (entry) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Row(
                children: <Widget>[
                  Expanded(child: Text(entry.key)),
                  Text(
                    entry.value,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
