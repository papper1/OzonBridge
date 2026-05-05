import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/widgets/app_card.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_badge.dart';
import '../../data/models/crawl_job.dart';
import '../../data/repositories/local_dashboard_repository.dart';
import '../../data/repositories/local_template_repository.dart';
import '../../data/repositories/mock_crawl_repository.dart';
import 'crawl_controller.dart';
import 'crawl_state.dart';
import 'widgets/crawl_config_summary.dart';
import 'widgets/progress_card.dart';

class CrawlScreen extends ConsumerWidget {
  const CrawlScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(crawlControllerProvider);
    final controller = ref.read(crawlControllerProvider.notifier);
    final repo = ref.watch(mockCrawlRepositoryProvider);
    final dashboardSnapshot = ref.watch(localDashboardSnapshotProvider);
    final templates = ref.watch(localTemplatesProvider).valueOrNull ?? const [];
    final templateItems = (templates.isEmpty ? repo.templates : templates)
        .map((template) => template.fileName)
        .toSet()
        .toList();
    final selectedTemplate = templateItems.contains(state.template)
        ? state.template
        : templateItems.first;

    if (selectedTemplate != state.template) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        controller.setTemplate(selectedTemplate);
      });
    }

    final jobs = _mergeRecentJobs(
      dashboardSnapshot.valueOrNull?.jobs ?? const <CrawlJob>[],
      state,
    );

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Thu thập dữ liệu',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'Frontend gọi backend local API để tạo job crawl và polling trạng thái theo thời gian thực.',
          ),
          const SizedBox(height: 16),
          AppCard(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                StatusBadge(
                  state.backendAvailable ? 'Backend online' : 'Backend offline',
                  color: state.backendAvailable
                      ? AppColors.success
                      : AppColors.error,
                ),
                const SizedBox(width: 12),
                Expanded(child: Text(state.backendMessage)),
                PrimaryButton(
                  label: 'Kiểm tra backend',
                  icon: Icons.wifi_find_rounded,
                  variant: ButtonVariant.secondary,
                  onPressed: state.isCheckingBackend
                      ? null
                      : controller.checkBackend,
                ),
              ],
            ),
          ),
          if (state.errorMessage != null) ...<Widget>[
            const SizedBox(height: 12),
            AppCard(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: <Widget>[
                  const Icon(
                    Icons.error_outline_rounded,
                    color: AppColors.error,
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Text(state.errorMessage!)),
                ],
              ),
            ),
          ],
          const SizedBox(height: AppSizes.sectionGap),
          Wrap(
            spacing: 12,
            children: const <String>[
              'URL sản phẩm',
              'Từ khóa',
              'Theo shop',
            ].map(
              (String tab) => ChoiceChip(
                label: Text(tab),
                selected: state.tab == tab,
                onSelected: (_) => controller.setTab(tab),
              ),
            ).toList(),
          ),
          const SizedBox(height: AppSizes.sectionGap),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                flex: 2,
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Tạo phiên crawl mới',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Chỉ giữ lại các tùy chọn đã được backend xử lý thật.',
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        maxLines: 6,
                        controller: TextEditingController(text: state.input),
                        onChanged: controller.setInput,
                        decoration: InputDecoration(
                          labelText: state.tab == 'Từ khóa'
                              ? 'Nhập từ khóa'
                              : state.tab == 'Theo shop'
                              ? 'Nhập shop URL'
                              : 'Nhập URL sản phẩm',
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Nguồn dữ liệu',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: repo.sources.map(
                          (String source) => ChoiceChip(
                            label: Text(source),
                            selected: state.source == source,
                            onSelected: (_) => controller.setSource(source),
                          ),
                        ).toList(),
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        initialValue: selectedTemplate,
                        decoration: const InputDecoration(
                          labelText: 'Template',
                        ),
                        items: templateItems.map(
                          (String fileName) => DropdownMenuItem<String>(
                            value: fileName,
                            child: Text(fileName),
                          ),
                        ).toList(),
                        onChanged: (String? value) {
                          if (value != null) {
                            controller.setTemplate(value);
                          }
                        },
                      ),
                      const SizedBox(height: 18),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.pageBackground,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Column(
                          children: <Widget>[
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title: const Text('Dịch tiếng Nga'),
                              subtitle: const Text(
                                'Gửi dữ liệu qua bước dịch của backend.',
                              ),
                              value: state.translateToRussian,
                              onChanged: controller.setTranslate,
                            ),
                            const Divider(height: 8),
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title: const Text('Export Excel'),
                              subtitle: const Text(
                                'Xuất file .xlsx sau khi xử lý xong.',
                              ),
                              value: state.exportExcel,
                              onChanged: controller.setExportExcel,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Kiểm tra dữ liệu',
                              icon: Icons.search_rounded,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                              onPressed: controller.checkBackend,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: PrimaryButton(
                              label: state.isSubmitting || state.isPolling
                                  ? 'Đang crawl...'
                                  : 'Bắt đầu crawl',
                              icon: Icons.play_arrow_rounded,
                              expanded: true,
                              onPressed: state.canStart
                                  ? controller.startCrawl
                                  : null,
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: PrimaryButton(
                              label: 'Lưu nháp',
                              icon: Icons.bookmark_border_rounded,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  children: <Widget>[
                    CrawlConfigSummary(state: state),
                    const SizedBox(height: 16),
                    ProgressCard(
                      status: state.activeJobStatus,
                      message: state.jobMessage,
                      processed: state.processed,
                      total: state.total,
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (state.liveResults.isNotEmpty) ...<Widget>[
            const SizedBox(height: AppSizes.sectionGap),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Text(
                        'Kết quả từ backend',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const Spacer(),
                      if (state.activeJobId != null)
                        Text(
                          'Job: ${state.activeJobId}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      PrimaryButton(
                        label: 'Translate',
                        icon: Icons.translate_rounded,
                        onPressed: controller.translateResults,
                      ),
                      PrimaryButton(
                        label: 'Map to Ozon',
                        icon: Icons.hub_outlined,
                        onPressed: controller.mapResults,
                      ),
                      PrimaryButton(
                        label: 'Export Excel',
                        icon: Icons.file_download_outlined,
                        onPressed: controller.exportResults,
                      ),
                    ],
                  ),
                  if (state.exportResult != null) ...<Widget>[
                    const SizedBox(height: 12),
                    Text('File: ${state.exportResult!.fileName}'),
                    const SizedBox(height: 4),
                    Text('Download: ${state.exportResult!.downloadUrl}'),
                  ],
                  const SizedBox(height: 12),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const <DataColumn>[
                        DataColumn(label: Text('ID')),
                        DataColumn(label: Text('Tên sản phẩm')),
                        DataColumn(label: Text('SKU')),
                        DataColumn(label: Text('Giá')),
                        DataColumn(label: Text('Dịch')),
                        DataColumn(label: Text('Map')),
                        DataColumn(label: Text('Export')),
                      ],
                      rows: state.liveResults.map(
                        (item) => DataRow(
                          cells: <DataCell>[
                            DataCell(Text(item.id)),
                            DataCell(Text(item.name)),
                            DataCell(Text(item.sku)),
                            DataCell(Text(item.price)),
                            DataCell(Text('${item.translation}%')),
                            DataCell(Text('${item.mapping}%')),
                            DataCell(
                              StatusBadge(
                                item.exported ? 'Đã export' : 'Chưa export',
                                color: item.exported
                                    ? AppColors.success
                                    : AppColors.warning,
                              ),
                            ),
                          ],
                        ),
                      ).toList(),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: AppSizes.sectionGap),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Phiên crawl gần đây',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                if (dashboardSnapshot.hasError && jobs.isEmpty)
                  const Text(
                    'Không đọc được lịch sử crawl local. Kiểm tra thư mục data/app.',
                  )
                else if (jobs.isEmpty)
                  const Text('Chưa có phiên crawl thực tế nào được ghi nhận.')
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const <DataColumn>[
                        DataColumn(label: Text('Mã phiên')),
                        DataColumn(label: Text('Nguồn')),
                        DataColumn(label: Text('Kiểu')),
                        DataColumn(label: Text('Đã xử lý')),
                        DataColumn(label: Text('Thành công')),
                        DataColumn(label: Text('Lỗi')),
                        DataColumn(label: Text('Trạng thái')),
                        DataColumn(label: Text('Thời gian')),
                      ],
                      rows: jobs.map(
                        (job) => DataRow(
                          cells: <DataCell>[
                            DataCell(Text(job.id)),
                            DataCell(Text(job.source)),
                            DataCell(Text(_jobModeLabel(job.mode))),
                            DataCell(Text('${job.processed}')),
                            DataCell(Text('${job.success}')),
                            DataCell(Text('${job.failed}')),
                            DataCell(
                              StatusBadge(
                                _jobStatusLabel(job.status),
                                color: _jobStatusColor(job.status),
                              ),
                            ),
                            DataCell(Text(_jobUpdatedAt(job))),
                          ],
                        ),
                      ).toList(),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<CrawlJob> _mergeRecentJobs(List<CrawlJob> jobs, CrawlState state) {
    final merged = <CrawlJob>[...jobs];
    final activeJobId = state.activeJobId;
    if (activeJobId == null || activeJobId.isEmpty) {
      return merged;
    }

    final activeJob = CrawlJob(
      id: activeJobId,
      status: state.activeJobStatus,
      message: state.jobMessage,
      source: state.source,
      mode: state.tab,
      total: state.total,
      processed: state.processed,
      success: state.liveResults.where((item) => item.status == 'success').length,
      failed: state.liveResults.where((item) => item.status == 'failed').length,
      updatedAt: DateTime.now().toLocal().toString(),
    );

    final existingIndex = merged.indexWhere((job) => job.id == activeJobId);
    if (existingIndex >= 0) {
      merged[existingIndex] = _preferMoreCompleteJob(merged[existingIndex], activeJob);
    } else {
      merged.insert(0, activeJob);
    }

    return merged;
  }

  CrawlJob _preferMoreCompleteJob(CrawlJob persisted, CrawlJob active) {
    final persistedLoad = persisted.processed + persisted.success + persisted.failed;
    final activeLoad = active.processed + active.success + active.failed;
    return activeLoad >= persistedLoad ? active : persisted;
  }

  String _jobStatusLabel(String status) {
    switch (status.trim().toLowerCase()) {
      case 'running':
        return 'Đang chạy';
      case 'success':
        return 'Hoàn tất';
      case 'failed':
        return 'Lỗi';
      case 'pending':
        return 'Chờ xử lý';
      default:
        return status;
    }
  }

  Color _jobStatusColor(String status) {
    switch (status.trim().toLowerCase()) {
      case 'running':
      case 'pending':
        return AppColors.primary;
      case 'success':
        return AppColors.success;
      default:
        return AppColors.error;
    }
  }

  String _jobModeLabel(String mode) {
    switch (mode.trim().toLowerCase()) {
      case 'product_url':
      case 'url sản phẩm':
        return 'URL sản phẩm';
      case 'keyword':
      case 'từ khóa':
        return 'Từ khóa';
      case 'shop_url':
      case 'theo shop':
        return 'Theo shop';
      default:
        return mode;
    }
  }

  String _jobUpdatedAt(CrawlJob job) {
    if (job.updatedAt.isEmpty) {
      return '-';
    }
    final parsed = DateTime.tryParse(job.updatedAt);
    if (parsed == null) {
      return job.updatedAt;
    }
    final local = parsed.toLocal();
    return '${_twoDigits(local.day)}/${_twoDigits(local.month)}/${local.year} '
        '${_twoDigits(local.hour)}:${_twoDigits(local.minute)}';
  }

  String _twoDigits(int value) => value.toString().padLeft(2, '0');
}
