import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/utils/text_utils.dart';
import '../../core/widgets/app_card.dart';
import '../../core/widgets/metric_card.dart';
import '../../core/widgets/status_badge.dart';
import '../../data/models/dashboard_summary.dart';
import '../../data/models/product_result.dart';
import '../../data/repositories/local_dashboard_repository.dart';
import '../../data/repositories/local_result_repository.dart';
import 'widgets/result_detail_panel.dart';

class ResultScreen extends ConsumerStatefulWidget {
  const ResultScreen({super.key});

  @override
  ConsumerState<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends ConsumerState<ResultScreen> {
  String _sourceFilter = 'Tất cả';
  String _statusFilter = 'Tất cả';
  String _searchQuery = '';
  String? _selectedId;

  @override
  Widget build(BuildContext context) {
    final resultsAsync = ref.watch(localResultsProvider);
    final dashboardAsync = ref.watch(localDashboardSnapshotProvider);
    final results = resultsAsync.valueOrNull ?? const <ProductResult>[];
    final summary =
        dashboardAsync.valueOrNull?.summary ?? const DashboardSummary.empty();
    final filteredResults = _applyFilters(results);
    final selected = _resolveSelected(filteredResults);

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Kết quả', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          const Text(
            'Đọc trực tiếp kết quả local từ clean data và job history.',
          ),
          const SizedBox(height: AppSizes.sectionGap),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: <Widget>[
              SizedBox(
                width: 260,
                child: MetricCard(
                  title: 'Phiên hoàn tất',
                  value: _formatInt(
                    results
                        .where((ProductResult item) => item.status == 'success')
                        .length,
                  ),
                  subtitle: 'Số record đã xử lý xong',
                  icon: Icons.task_alt_rounded,
                  accent: AppColors.primary,
                ),
              ),
              SizedBox(
                width: 260,
                child: MetricCard(
                  title: 'Sản phẩm sẵn sàng export',
                  value: _formatInt(
                    results
                        .where((ProductResult item) => item.mapping > 0)
                        .length,
                  ),
                  subtitle: 'Đọc từ dữ liệu thực tế',
                  icon: Icons.inventory_2_outlined,
                  accent: AppColors.success,
                ),
              ),
              SizedBox(
                width: 260,
                child: MetricCard(
                  title: 'File Excel đã tạo',
                  value: _formatInt(summary.exportedFiles),
                  subtitle: 'Đếm trong thư mục export',
                  icon: Icons.file_download_outlined,
                  accent: AppColors.warning,
                ),
              ),
              SizedBox(
                width: 260,
                child: MetricCard(
                  title: 'Tỷ lệ hợp lệ',
                  value: '${summary.successRate.toStringAsFixed(1)}%',
                  subtitle: 'Tính từ dữ liệu local',
                  icon: Icons.pie_chart_outline_rounded,
                  accent: AppColors.primaryAlt,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSizes.sectionGap),
          AppCard(
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              children: <Widget>[
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    initialValue: _sourceFilter,
                    items: <String>{
                      'Tất cả',
                      ...results.map(
                        (ProductResult item) =>
                            sanitizeDisplayText(item.source),
                      ),
                    }.map((String source) {
                      return DropdownMenuItem<String>(
                        value: source,
                        child: Text(source),
                      );
                    }).toList(),
                    onChanged: (String? value) {
                      if (value == null) {
                        return;
                      }
                      setState(() => _sourceFilter = value);
                    },
                    decoration: const InputDecoration(labelText: 'Nguồn'),
                  ),
                ),
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    initialValue: _statusFilter,
                    items: const <String>[
                      'Tất cả',
                      'success',
                      'pending',
                      'failed',
                    ].map((String status) {
                      return DropdownMenuItem<String>(
                        value: status,
                        child: Text(_statusLabel(status)),
                      );
                    }).toList(),
                    onChanged: (String? value) {
                      if (value == null) {
                        return;
                      }
                      setState(() => _statusFilter = value);
                    },
                    decoration: const InputDecoration(labelText: 'Trạng thái'),
                  ),
                ),
                SizedBox(
                  width: 320,
                  child: TextField(
                    onChanged: (String value) {
                      setState(() => _searchQuery = value.trim().toLowerCase());
                    },
                    decoration: const InputDecoration(
                      labelText: 'Tìm theo mã, tên hoặc SKU',
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSizes.sectionGap),
          if (resultsAsync.hasError)
            Text(
              'Không đọc được dữ liệu kết quả local.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.error,
              ),
            ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                flex: 2,
                child: AppCard(
                  child: filteredResults.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.symmetric(vertical: 24),
                          child: Text(
                            'Chưa có kết quả local phù hợp bộ lọc.',
                          ),
                        )
                      : SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: DataTable(
                            columns: const <DataColumn>[
                              DataColumn(label: Text('Mã kết quả')),
                              DataColumn(label: Text('Nguồn')),
                              DataColumn(label: Text('Số sản phẩm')),
                              DataColumn(label: Text('Mapping')),
                              DataColumn(label: Text('Dịch')),
                              DataColumn(label: Text('Export')),
                              DataColumn(label: Text('Thời gian')),
                              DataColumn(label: Text('Trạng thái')),
                            ],
                            rows: filteredResults.map((ProductResult item) {
                              final isSelected = selected?.id == item.id;
                              return DataRow(
                                selected: isSelected,
                                onSelectChanged: (_) {
                                  setState(() => _selectedId = item.id);
                                },
                                cells: <DataCell>[
                                  DataCell(
                                    Text(sanitizeDisplayText(item.id)),
                                  ),
                                  DataCell(
                                    Text(
                                      sanitizeDisplayText(item.source),
                                    ),
                                  ),
                                  DataCell(Text('${item.productCount}')),
                                  DataCell(Text('${item.mapping}%')),
                                  DataCell(Text('${item.translation}%')),
                                  DataCell(
                                    Icon(
                                      item.exported
                                          ? Icons.check_circle_rounded
                                          : Icons.pending_outlined,
                                      color: item.exported
                                          ? AppColors.success
                                          : AppColors.warning,
                                    ),
                                  ),
                                  DataCell(Text(_formatDate(item.updatedAt))),
                                  DataCell(
                                    StatusBadge(
                                      _statusLabel(item.status),
                                      color: _statusColor(item.status),
                                    ),
                                  ),
                                ],
                              );
                            }).toList(),
                          ),
                        ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: ResultDetailPanel(
                  result: selected,
                  emptyMessage: 'Chọn một kết quả để xem chi tiết.',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  List<ProductResult> _applyFilters(List<ProductResult> results) {
    return results.where((ProductResult item) {
      final matchesSource = _sourceFilter == 'Tất cả' ||
          sanitizeDisplayText(item.source) == _sourceFilter;
      final matchesStatus =
          _statusFilter == 'Tất cả' || item.status == _statusFilter;
      final haystack =
          '${item.id} ${item.name} ${item.sku}'.toLowerCase();
      final matchesSearch =
          _searchQuery.isEmpty || haystack.contains(_searchQuery);
      return matchesSource && matchesStatus && matchesSearch;
    }).toList();
  }

  ProductResult? _resolveSelected(List<ProductResult> filteredResults) {
    if (filteredResults.isEmpty) {
      return null;
    }
    if (_selectedId == null) {
      return filteredResults.first;
    }
    for (final item in filteredResults) {
      if (item.id == _selectedId) {
        return item;
      }
    }
    return filteredResults.first;
  }
}

Color _statusColor(String status) {
  switch (status.trim().toLowerCase()) {
    case 'success':
      return AppColors.success;
    case 'failed':
      return AppColors.error;
    case 'pending':
      return AppColors.warning;
    default:
      return AppColors.primary;
  }
}

String _statusLabel(String status) {
  switch (status.trim().toLowerCase()) {
    case 'success':
      return 'Hoàn tất';
    case 'failed':
      return 'Lỗi';
    case 'pending':
      return 'Chờ xử lý';
    case 'tất cả':
      return 'Tất cả';
    default:
      return status;
  }
}

String _formatInt(int value) {
  final text = value.toString();
  return text.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => ',',
  );
}

String _formatDate(String value) {
  if (value.isEmpty) {
    return '-';
  }
  return value.replaceFirst('T', ' ').replaceFirst('Z', '');
}
