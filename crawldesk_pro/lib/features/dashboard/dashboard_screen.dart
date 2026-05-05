import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/widgets/app_card.dart';
import '../../core/widgets/metric_card.dart';
import '../../core/widgets/status_badge.dart';
import '../../data/models/crawl_job.dart';
import '../../data/models/dashboard_summary.dart';
import '../../data/models/product_result.dart';
import '../../data/repositories/local_dashboard_repository.dart';
import '../crawl/crawl_controller.dart';
import 'widgets/quick_crawl_card.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshotAsync = ref.watch(localDashboardSnapshotProvider);
    final crawlState = ref.watch(crawlControllerProvider);
    final summary =
        snapshotAsync.valueOrNull?.summary ?? const DashboardSummary.empty();
    final jobs = snapshotAsync.valueOrNull?.jobs ?? const <CrawlJob>[];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Tổng quan', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          const Text(
            'Dashboard gọn cho workflow crawl, làm sạch, dịch, mapping và export.',
          ),
          const SizedBox(height: AppSizes.sectionGap),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: <Widget>[
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Nguồn hỗ trợ',
                  value: _formatInt(summary.supportedSources.length),
                  subtitle: summary.supportedSources.isEmpty
                      ? 'Chưa có dữ liệu nguồn'
                      : summary.supportedSources.join(', '),
                  icon: Icons.language_rounded,
                  accent: AppColors.info,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Sản phẩm đã crawl',
                  value: _formatInt(summary.totalCrawledProducts),
                  subtitle: 'Đọc từ dữ liệu clean thực tế',
                  icon: Icons.inventory_2_outlined,
                  accent: AppColors.success,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Tỷ lệ thành công',
                  value: '${summary.successRate.toStringAsFixed(1)}%',
                  subtitle: 'Tính từ job history và dữ liệu local',
                  icon: Icons.show_chart_rounded,
                  accent: AppColors.primaryAlt,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'File export',
                  value: _formatInt(summary.exportedFiles),
                  subtitle: 'Excel đã xuất thành công',
                  icon: Icons.table_chart_rounded,
                  accent: AppColors.warning,
                ),
              ),
            ],
          ),
          if (snapshotAsync.hasError) ...<Widget>[
            const SizedBox(height: 12),
            Text(
              'Không đọc được dữ liệu local. Kiểm tra thư mục data/app.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.error,
              ),
            ),
          ],
          const SizedBox(height: AppSizes.sectionGap),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Expanded(flex: 2, child: QuickCrawlCard()),
              const SizedBox(width: 16),
              Expanded(
                child: _LivePipelineCard(
                  processed: crawlState.processed,
                  total: crawlState.total,
                  stage: crawlState.stage,
                  status: crawlState.activeJobStatus,
                  message: crawlState.jobMessage,
                  results: crawlState.liveResults,
                  translateEnabled: crawlState.translateToRussian,
                  exportEnabled: crawlState.exportExcel,
                  isBusy: crawlState.isSubmitting || crawlState.isPolling,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSizes.sectionGap),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Phiên gần đây',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                if (jobs.isEmpty)
                  const Text('Chưa có phiên crawl thực tế được ghi nhận.')
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const <DataColumn>[
                        DataColumn(label: Text('Mã phiên')),
                        DataColumn(label: Text('Nguồn')),
                        DataColumn(label: Text('Tổng mục')),
                        DataColumn(label: Text('Thành công')),
                        DataColumn(label: Text('Lỗi')),
                        DataColumn(label: Text('Trạng thái')),
                        DataColumn(label: Text('Cập nhật')),
                      ],
                      rows: jobs
                          .map(
                            (job) => DataRow(
                              cells: <DataCell>[
                                DataCell(Text(job.id)),
                                DataCell(Text(job.source)),
                                DataCell(Text(_formatInt(job.total))),
                                DataCell(Text(_formatInt(job.success))),
                                DataCell(Text(_formatInt(job.failed))),
                                DataCell(
                                  StatusBadge(
                                    _statusLabel(job.status),
                                    color: _statusColor(job.status),
                                  ),
                                ),
                                DataCell(Text(job.updatedAt)),
                              ],
                            ),
                          )
                          .toList(),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LivePipelineCard extends StatelessWidget {
  const _LivePipelineCard({
    required this.processed,
    required this.total,
    required this.stage,
    required this.status,
    required this.message,
    required this.results,
    required this.translateEnabled,
    required this.exportEnabled,
    required this.isBusy,
  });

  final int processed;
  final int total;
  final String stage;
  final String status;
  final String message;
  final List<ProductResult> results;
  final bool translateEnabled;
  final bool exportEnabled;
  final bool isBusy;

  @override
  Widget build(BuildContext context) {
    final normalizedStage = stage.trim().toLowerCase();
    final crawlCount = processed;
    final cleanCount = results.length;
    final translateCount =
        results.where((ProductResult item) => item.translation > 0).length;
    final mapCount =
        results.where((ProductResult item) => item.mapping > 0).length;
    final exportCount =
        results.where((ProductResult item) => item.exported).length;
    final progress = total > 0
        ? (processed / total).clamp(0.0, 1.0).toDouble()
        : 0.0;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Pipeline xử lý',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              StatusBadge(
                _pipelineStatusLabel(status, isBusy),
                color: _statusColor(status),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  message.isEmpty
                      ? 'Chưa có job đang chạy'
                      : message,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          LinearProgressIndicator(
            value: isBusy ? progress : (status == 'success' ? 1 : 0),
            minHeight: 8,
            borderRadius: BorderRadius.circular(999),
            backgroundColor: AppColors.primarySoft,
          ),
          const SizedBox(height: 10),
          Text(
            total > 0
                ? '${_formatInt(processed)} / ${_formatInt(total)} sản phẩm'
                : 'Đang chờ phiên crawl mới',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 18),
          _PipelineStep(
            title: 'Crawl',
            subtitle: 'Thu thập dữ liệu',
            detail: '$crawlCount item',
            icon: Icons.travel_explore_rounded,
            state: _stageState(
              stage: normalizedStage,
              stageKey: 'crawl',
              count: crawlCount,
              total: total,
              isBusy: isBusy,
            ),
          ),
          const _ArrowDivider(),
          _PipelineStep(
            title: 'Làm sạch',
            subtitle: 'Chuẩn hóa dữ liệu',
            detail: '$cleanCount item',
            icon: Icons.auto_fix_high_rounded,
            state: _stageState(
              stage: normalizedStage,
              stageKey: 'clean',
              count: cleanCount,
              total: total,
              isBusy: isBusy,
            ),
          ),
          const _ArrowDivider(),
          _PipelineStep(
            title: 'Dịch',
            subtitle: translateEnabled ? 'Google Translate style' : 'Tắt ở phiên hiện tại',
            detail: '$translateCount item',
            icon: Icons.g_translate_rounded,
            state: translateEnabled
                ? _stageState(
                    stage: normalizedStage,
                    stageKey: 'translate',
                    count: translateCount,
                    total: total,
                    isBusy: isBusy,
                  )
                : _PipelineVisualState.pending,
          ),
          const _ArrowDivider(),
          _PipelineStep(
            title: 'Map Ozon',
            subtitle: 'Ánh xạ field sang Ozon',
            detail: '$mapCount item',
            icon: Icons.account_tree_rounded,
            state: _stageState(
              stage: normalizedStage,
              stageKey: 'map',
              count: mapCount,
              total: total,
              isBusy: isBusy,
            ),
          ),
          const _ArrowDivider(),
          _PipelineStep(
            title: 'Excel',
            subtitle: exportEnabled ? 'Xuất file .xlsx' : 'Tắt export ở phiên hiện tại',
            detail: '$exportCount file',
            icon: Icons.table_chart_rounded,
            state: exportEnabled
                ? _stageState(
                    stage: normalizedStage,
                    stageKey: 'export',
                    count: exportCount,
                    total: total,
                    isBusy: isBusy,
                  )
                : _PipelineVisualState.pending,
          ),
        ],
      ),
    );
  }
}

enum _PipelineVisualState { pending, active, complete }

_PipelineVisualState _stageState({
  required String stage,
  required String stageKey,
  required int count,
  required int total,
  required bool isBusy,
}) {
  if (count > 0 && total > 0 && count >= total) {
    return _PipelineVisualState.complete;
  }
  if (stage == stageKey) {
    return _PipelineVisualState.active;
  }
  if (stageKey == 'translate' && stage == 'map' && count > 0) {
    return _PipelineVisualState.complete;
  }
  if (count > 0) {
    return _PipelineVisualState.complete;
  }
  if (isBusy && stageKey == 'crawl' && stage == 'prepare') {
    return _PipelineVisualState.active;
  }
  return _PipelineVisualState.pending;
}

class _PipelineStep extends StatelessWidget {
  const _PipelineStep({
    required this.title,
    required this.subtitle,
    required this.detail,
    required this.icon,
    required this.state,
  });

  final String title;
  final String subtitle;
  final String detail;
  final IconData icon;
  final _PipelineVisualState state;

  @override
  Widget build(BuildContext context) {
    final accent = switch (state) {
      _PipelineVisualState.complete => AppColors.success,
      _PipelineVisualState.active => AppColors.primary,
      _PipelineVisualState.pending => AppColors.textSecondary,
    };
    final background = switch (state) {
      _PipelineVisualState.complete => const Color(0xFFEAF8EF),
      _PipelineVisualState.active => const Color(0xFFE8EEFF),
      _PipelineVisualState.pending => const Color(0xFFF1F5F9),
    };

    return Row(
      children: <Widget>[
        AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: background,
            borderRadius: BorderRadius.circular(16),
            boxShadow: state == _PipelineVisualState.active
                ? const <BoxShadow>[
                    BoxShadow(
                      color: Color(0x332563EB),
                      blurRadius: 14,
                      offset: Offset(0, 6),
                    ),
                  ]
                : null,
          ),
          child: Icon(icon, color: accent, size: 26),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      title,
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        color: accent == AppColors.textSecondary
                            ? AppColors.textPrimary
                            : accent,
                      ),
                    ),
                  ),
                  Text(
                    detail,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: accent,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ArrowDivider extends StatelessWidget {
  const _ArrowDivider();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 10),
      child: Center(
        child: Icon(
          Icons.arrow_downward_rounded,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}

Color _statusColor(String status) {
  switch (status.trim().toLowerCase()) {
    case 'success':
      return AppColors.success;
    case 'running':
    case 'pending':
      return AppColors.primary;
    case 'failed':
      return AppColors.error;
    default:
      return AppColors.textSecondary;
  }
}

String _statusLabel(String status) {
  switch (status.trim().toLowerCase()) {
    case 'success':
      return 'Hoàn tất';
    case 'running':
      return 'Đang chạy';
    case 'pending':
      return 'Chờ xử lý';
    case 'failed':
      return 'Lỗi';
    default:
      return status;
  }
}

String _pipelineStatusLabel(String status, bool isBusy) {
  if (isBusy) {
    return 'Live';
  }
  return _statusLabel(status);
}

String _formatInt(int value) {
  final text = value.toString();
  return text.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => ',',
  );
}
