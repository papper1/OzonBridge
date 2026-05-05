import 'dart:io';

import 'package:flutter/material.dart';

import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../data/models/ozon_template.dart';

class TemplateDetailCard extends StatelessWidget {
  const TemplateDetailCard({
    required this.template,
    super.key,
  });

  final OzonTemplate? template;

  @override
  Widget build(BuildContext context) {
    if (template == null) {
      return const AppCard(
        child: SizedBox(
          height: 220,
          child: Center(child: Text('Chọn một template để xem chi tiết.')),
        ),
      );
    }

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Chi tiết template: ${template!.name}',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _Meta(label: 'Tên file', value: template!.fileName),
              _Meta(label: 'Danh mục', value: template!.category),
              _Meta(
                label: 'Trường bắt buộc',
                value: '${template!.requiredFieldCount}',
              ),
              _Meta(label: 'Phiên bản', value: template!.version),
              _Meta(label: 'Sheet', value: template!.sheetName),
              _Meta(label: 'Field map', value: '${template!.fieldCount}'),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              PrimaryButton(
                label: 'Mở file Excel',
                icon: Icons.table_chart_rounded,
                onPressed: template!.workbookAbsolutePath.isEmpty
                    ? null
                    : () => _openPath(template!.workbookAbsolutePath),
              ),
              PrimaryButton(
                label: 'Mở JSON config',
                icon: Icons.data_object_rounded,
                variant: ButtonVariant.secondary,
                onPressed: () => _openPath(template!.jsonFilePath),
              ),
              PrimaryButton(
                label: 'Mở thư mục',
                icon: Icons.folder_open_rounded,
                variant: ButtonVariant.secondary,
                onPressed: () => _openFolder(File(template!.jsonFilePath).parent.path),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Required fields',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: template!.requiredFields
                .map((String field) => Chip(label: Text(field)))
                .toList(),
          ),
          const SizedBox(height: 16),
          Text(
            'Field map columns',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 10),
          if (template!.fieldMapKeys.isEmpty)
            const Text('Template này chưa có field map.')
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: template!.fieldMapKeys
                  .map((String field) => Chip(label: Text(field)))
                  .toList(),
            ),
        ],
      ),
    );
  }
}

class _Meta extends StatelessWidget {
  const _Meta({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

Future<void> _openPath(String path) async {
  if (path.isEmpty) {
    return;
  }
  final file = File(path);
  if (!file.existsSync()) {
    return;
  }
  if (Platform.isWindows) {
    await Process.start('cmd', <String>['/c', 'start', '', path]);
    return;
  }
  await Process.start(path, const <String>[]);
}

Future<void> _openFolder(String path) async {
  if (path.isEmpty) {
    return;
  }
  final directory = Directory(path);
  if (!directory.existsSync()) {
    return;
  }
  if (Platform.isWindows) {
    await Process.start('explorer.exe', <String>[path]);
    return;
  }
  await Process.start(path, const <String>[]);
}
