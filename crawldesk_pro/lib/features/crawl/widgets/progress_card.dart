import 'package:flutter/material.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_badge.dart';

class ProgressCard extends StatelessWidget {
  const ProgressCard({
    required this.status,
    required this.message,
    required this.processed,
    required this.total,
    super.key,
  });

  final String status;
  final String message;
  final int processed;
  final int total;

  @override
  Widget build(BuildContext context) {
    final value = total == 0 ? 0.0 : processed / total;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(
                'Tiến trình crawl',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              StatusBadge(_statusLabel(status), color: _statusColor(status)),
            ],
          ),
          const SizedBox(height: 12),
          Text(message.isEmpty ? 'Chưa có phiên crawl nào chạy' : message),
          const SizedBox(height: 12),
          LinearProgressIndicator(value: value, minHeight: 8),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _Counter(label: 'Đã xử lý', value: '$processed'),
              _Counter(label: 'Tổng mục', value: '$total'),
              _Counter(
                label: 'Còn lại',
                value: '${(total - processed).clamp(0, total)}',
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _statusLabel(String value) {
    switch (value) {
      case 'running':
        return 'Đang chạy';
      case 'success':
        return 'Hoàn tất';
      case 'failed':
        return 'Lỗi';
      default:
        return 'Chờ';
    }
  }

  Color _statusColor(String value) {
    switch (value) {
      case 'running':
        return AppColors.primary;
      case 'success':
        return AppColors.success;
      case 'failed':
        return AppColors.error;
      default:
        return AppColors.warning;
    }
  }
}

class _Counter extends StatelessWidget {
  const _Counter({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 126,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.w800,
              fontSize: 22,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
