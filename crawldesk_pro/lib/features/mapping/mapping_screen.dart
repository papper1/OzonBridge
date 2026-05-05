import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/widgets/app_card.dart';
import '../../core/widgets/metric_card.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_badge.dart';
import 'widgets/mapping_table_card.dart';

class MappingScreen extends StatelessWidget {
  const MappingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const sourceFields = <String>[
      'product_title',
      'price',
      'images',
      'category',
      'stock',
      'material',
      'color',
      'size',
    ];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Mapping Ozon',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'Ánh xạ dữ liệu từ nguồn crawl sang template Ozon theo cấu hình gọn.',
          ),
          const SizedBox(height: AppSizes.sectionGap),
          const Wrap(
            spacing: 16,
            runSpacing: 16,
            children: <Widget>[
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Template',
                  value: 'OZON_Template_v3.1',
                  subtitle: 'Hoodie / Fashion',
                  icon: Icons.description_outlined,
                  accent: AppColors.primary,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Số sản phẩm',
                  value: '4,000',
                  subtitle: 'Tổng sản phẩm đầu vào',
                  icon: Icons.shopping_bag_outlined,
                  accent: AppColors.info,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Tiến độ mapping',
                  value: '86.3%',
                  subtitle: 'Đã map 18/21 trường',
                  icon: Icons.check_circle_outline_rounded,
                  accent: AppColors.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSizes.sectionGap),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Nguồn dữ liệu từ crawl',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      ...sourceFields.map(
                        (String field) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.drag_indicator_rounded),
                          title: Text(field),
                          subtitle: Text(
                            field == 'product_title'
                                ? 'Áo hoodie nam nữ unisex oversize'
                                : field == 'price'
                                ? '¥89.00'
                                : field == 'images'
                                ? '5 ảnh nguồn'
                                : 'Mock value',
                          ),
                          trailing: const Icon(
                            Icons.add_circle_outline_rounded,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),
              const Expanded(flex: 2, child: MappingTableCard()),
              const SizedBox(width: 16),
              Expanded(
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Preview sản phẩm',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      Container(
                        height: 200,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          gradient: const LinearGradient(
                            colors: <Color>[
                              Color(0xFFFFFAF4),
                              Color(0xFFF2EFE7),
                            ],
                          ),
                        ),
                        child: const Center(
                          child: Icon(Icons.checkroom_rounded, size: 84),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Áo hoodie nam nữ unisex oversize',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 12),
                      const StatusBadge(
                        'Cần rà soát 3 trường',
                        color: AppColors.warning,
                      ),
                      const SizedBox(height: 16),
                      const Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Gợi ý bằng AI',
                              icon: Icons.auto_awesome_rounded,
                              expanded: true,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Validate',
                              icon: Icons.rule_rounded,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Áp dụng mapping',
                              icon: Icons.task_alt_rounded,
                              expanded: true,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Xuất thử Excel',
                              icon: Icons.file_download_outlined,
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
            ],
          ),
        ],
      ),
    );
  }
}
