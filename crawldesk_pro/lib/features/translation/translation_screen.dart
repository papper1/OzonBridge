import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/widgets/app_card.dart';
import '../../core/widgets/metric_card.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_badge.dart';
import 'widgets/translation_editors.dart';

class TranslationScreen extends StatelessWidget {
  const TranslationScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Dịch tiếng Nga',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'Biên tập nội dung dịch nhanh với mock model AI và bộ thuộc tính đơn giản.',
          ),
          const SizedBox(height: AppSizes.sectionGap),
          const Wrap(
            spacing: 16,
            runSpacing: 16,
            children: <Widget>[
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Cần dịch',
                  value: '2,734',
                  subtitle: '100% trong hàng đợi',
                  icon: Icons.edit_note_rounded,
                  accent: AppColors.primary,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Đã dịch',
                  value: '2,132',
                  subtitle: '77.9% hoàn thành',
                  icon: Icons.check_circle_outline_rounded,
                  accent: AppColors.success,
                ),
              ),
              SizedBox(
                width: 270,
                child: MetricCard(
                  title: 'Cần rà soát',
                  value: '134',
                  subtitle: 'Ưu tiên tiêu đề và giá',
                  icon: Icons.visibility_outlined,
                  accent: AppColors.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSizes.sectionGap),
          AppCard(
            child: Wrap(
              spacing: 16,
              runSpacing: 16,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: <Widget>[
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    initialValue: 'Trung / Anh / Việt',
                    decoration: const InputDecoration(
                      labelText: 'Ngôn ngữ nguồn',
                    ),
                    items:
                        const <String>[
                              'Trung / Anh / Việt',
                              'Tiếng Anh',
                              'Tiếng Việt',
                            ]
                            .map(
                              (String value) => DropdownMenuItem<String>(
                                value: value,
                                child: Text(value),
                              ),
                            )
                            .toList(),
                    onChanged: (_) {},
                  ),
                ),
                SizedBox(
                  width: 220,
                  child: DropdownButtonFormField<String>(
                    initialValue: 'GPT-4o (Mock)',
                    decoration: const InputDecoration(labelText: 'Model AI'),
                    items:
                        const <String>[
                              'GPT-4o (Mock)',
                              'GPT-4.1 mini',
                              'Deep translation',
                            ]
                            .map(
                              (String value) => DropdownMenuItem<String>(
                                value: value,
                                child: Text(value),
                              ),
                            )
                            .toList(),
                    onChanged: (_) {},
                  ),
                ),
                const SizedBox(
                  width: 220,
                  child: SwitchListTile(
                    title: Text('Giữ thương hiệu'),
                    value: true,
                    onChanged: null,
                  ),
                ),
                const SizedBox(
                  width: 220,
                  child: SwitchListTile(
                    title: Text('Ưu tiên thuật ngữ'),
                    value: true,
                    onChanged: null,
                  ),
                ),
                const PrimaryButton(
                  label: 'Dịch hàng loạt',
                  icon: Icons.play_arrow_rounded,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSizes.sectionGap),
          const TranslationEditors(),
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
                        'Bảng thuộc tính dịch',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: DataTable(
                          columns: const <DataColumn>[
                            DataColumn(label: Text('Thuộc tính gốc')),
                            DataColumn(label: Text('Giá trị gốc')),
                            DataColumn(label: Text('Giá trị tiếng Nga')),
                            DataColumn(label: Text('Trạng thái')),
                          ],
                          rows: const <DataRow>[
                            DataRow(
                              cells: <DataCell>[
                                DataCell(Text('Màu sắc')),
                                DataCell(Text('Be (Ivory)')),
                                DataCell(Text('Бежевый (Ivory)')),
                                DataCell(StatusBadge('Đã dịch')),
                              ],
                            ),
                            DataRow(
                              cells: <DataCell>[
                                DataCell(Text('Kích thước')),
                                DataCell(Text('L')),
                                DataCell(Text('L')),
                                DataCell(StatusBadge('Đã dịch')),
                              ],
                            ),
                            DataRow(
                              cells: <DataCell>[
                                DataCell(Text('Giá')),
                                DataCell(Text('¥89.00')),
                                DataCell(Text('₽8900')),
                                DataCell(
                                  StatusBadge(
                                    'Cần rà soát',
                                    color: AppColors.warning,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Quy tắc dịch',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 12),
                      const _Rule('Giữ nguyên SKU, MPN, mã vạch'),
                      const _Rule('Giữ nguyên tên thương hiệu'),
                      const _Rule('Không dịch tên dòng sản phẩm'),
                      const _Rule('Quy đổi đơn vị cm → см, kg → кг'),
                      const SizedBox(height: 16),
                      const Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Lưu bản dịch',
                              icon: Icons.save_outlined,
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
                              label: 'Xuất JSON',
                              icon: Icons.data_object_rounded,
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

class _Rule extends StatelessWidget {
  const _Rule(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: <Widget>[
          const Icon(
            Icons.check_circle_outline_rounded,
            size: 18,
            color: AppColors.success,
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
