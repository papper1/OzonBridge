import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../data/repositories/local_template_repository.dart';
import '../../crawl/crawl_controller.dart';

class QuickCrawlCard extends ConsumerStatefulWidget {
  const QuickCrawlCard({super.key});

  @override
  ConsumerState<QuickCrawlCard> createState() => _QuickCrawlCardState();
}

class _QuickCrawlCardState extends ConsumerState<QuickCrawlCard> {
  late final TextEditingController _inputController;
  String _source = '1688';
  String _template = 'OZON_Template_v3.1.xlsx';
  bool _translateToRussian = true;
  bool _exportExcel = true;

  @override
  void initState() {
    super.initState();
    _inputController = TextEditingController();
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _startQuickCrawl() async {
    final input = _inputController.text.trim();
    if (input.isEmpty) {
      return;
    }

    final controller = ref.read(crawlControllerProvider.notifier);
    controller.setTab('URL sản phẩm');
    controller.setSource(_source);
    controller.setTemplate(_template);
    controller.setTranslate(_translateToRussian);
    controller.setExportExcel(_exportExcel);
    controller.setInput(input);

    await controller.startCrawl();
    if (mounted) {
      context.go('/crawl');
    }
  }

  @override
  Widget build(BuildContext context) {
    final crawlState = ref.watch(crawlControllerProvider);
    final templates = ref.watch(localTemplatesProvider).valueOrNull ?? const [];
    final templateItems = templates.isEmpty
        ? const <String>['OZON_Template_v3.1.xlsx']
        : templates.map((template) => template.fileName).toSet().toList();
    final selectedTemplate = templateItems.contains(_template)
        ? _template
        : templateItems.first;
    if (selectedTemplate != _template) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          setState(() => _template = selectedTemplate);
        }
      });
    }
    final isBusy = crawlState.isSubmitting || crawlState.isPolling;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Tạo phiên crawl nhanh',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const Text(
            'Dán nhiều URL sản phẩm và khởi chạy pipeline ngay từ dashboard.',
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _inputController,
            maxLines: 5,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              hintText: 'Mỗi dòng một URL hoặc SKU nguồn...',
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _DropdownField(
                label: 'Nguồn',
                value: _source,
                items: const <String>['1688', 'SHEIN', 'Etsy', 'eBay'],
                onChanged: (String? value) {
                  if (value != null) {
                    setState(() => _source = value);
                  }
                },
              ),
              _DropdownField(
                label: 'Template',
                value: selectedTemplate,
                items: templateItems,
                onChanged: (String? value) {
                  if (value != null) {
                    setState(() => _template = value);
                  }
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            children: <Widget>[
              FilterChip(
                label: const Text('Dịch tiếng Nga'),
                selected: _translateToRussian,
                onSelected: (bool value) {
                  setState(() => _translateToRussian = value);
                },
              ),
              FilterChip(
                label: const Text('Export Excel'),
                selected: _exportExcel,
                onSelected: (bool value) {
                  setState(() => _exportExcel = value);
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
          PrimaryButton(
            label: isBusy ? 'Đang crawl...' : 'Bắt đầu crawl',
            icon: Icons.play_arrow_rounded,
            onPressed: inputReady && !isBusy ? _startQuickCrawl : null,
          ),
        ],
      ),
    );
  }

  bool get inputReady => _inputController.text.trim().isNotEmpty;
}

class _DropdownField extends StatelessWidget {
  const _DropdownField({
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final String label;
  final String value;
  final List<String> items;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 240,
      child: DropdownButtonFormField<String>(
        isExpanded: true,
        initialValue: value,
        decoration: InputDecoration(labelText: label),
        items: items
            .map(
              (String item) =>
                  DropdownMenuItem<String>(value: item, child: Text(item)),
            )
            .toList(),
        onChanged: onChanged,
      ),
    );
  }
}
