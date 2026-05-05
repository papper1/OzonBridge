import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/text_utils.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../data/models/product_result.dart';

class ResultDetailPanel extends StatelessWidget {
  const ResultDetailPanel({
    required this.result,
    this.emptyMessage = 'Không có dữ liệu.',
    super.key,
  });

  final ProductResult? result;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    if (result == null) {
      return AppCard(
        child: SizedBox(
          height: 320,
          child: Center(child: Text(emptyMessage)),
        ),
      );
    }

    final payload = _sanitizePayload(_buildPreviewPayload(result!));
    final prettyJson = const JsonEncoder.withIndent('  ').convert(payload);
    final imageUrl = _firstImage(result!);
    final canOpenExport = result!.exportFilePath.isNotEmpty;
    final canOpenJson =
        result!.normalizedFilePath.isNotEmpty || result!.rawFilePath.isNotEmpty;
    final folderPath = _resolveFolderPath(result!);
    final canOpenFolder = folderPath.isNotEmpty;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text(
                'Chi tiết kết quả',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              Icon(
                result!.exported
                    ? Icons.check_circle_rounded
                    : Icons.pending_outlined,
                color: result!.exported
                    ? AppColors.success
                    : AppColors.warning,
              ),
            ],
          ),
          const SizedBox(height: 16),
          _PreviewImage(imageUrl: imageUrl),
          const SizedBox(height: 16),
          Text(
            sanitizeDisplayText(result!.name),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          _Row(label: 'SKU', value: sanitizeDisplayText(result!.sku)),
          _Row(label: 'Giá', value: sanitizeDisplayText(result!.price)),
          _Row(label: 'Nguồn', value: sanitizeDisplayText(result!.source)),
          _Row(
            label: 'URL',
            value: result!.productUrl.isEmpty
                ? '-'
                : sanitizeDisplayText(result!.productUrl),
          ),
          const SizedBox(height: 8),
          StatusBadge(
            _statusLabel(result!.status),
            color: _statusColor(result!.status),
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(
                child: PrimaryButton(
                  label: canOpenExport ? 'Mở Excel' : 'Chưa có Excel',
                  icon:
                      canOpenExport ? Icons.download_rounded : Icons.pending_outlined,
                  expanded: true,
                  onPressed:
                      canOpenExport ? () => _openPath(result!.exportFilePath) : null,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: PrimaryButton(
                  label: canOpenJson ? 'Mở JSON thật' : 'Chưa có JSON',
                  icon: Icons.data_object_rounded,
                  expanded: true,
                  variant: ButtonVariant.secondary,
                  onPressed: canOpenJson
                      ? () => _openPath(
                            result!.normalizedFilePath.isNotEmpty
                                ? result!.normalizedFilePath
                                : result!.rawFilePath,
                          )
                      : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: PrimaryButton(
              label: canOpenFolder ? 'Mở thư mục chứa file' : 'Chưa có thư mục',
              icon: Icons.folder_open_rounded,
              expanded: true,
              variant: ButtonVariant.secondary,
              onPressed: canOpenFolder ? () => _openFolder(folderPath) : null,
            ),
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(14),
            ),
            child: SelectableText(
              prettyJson,
              style: const TextStyle(
                fontFamily: 'monospace',
                color: Colors.white,
                height: 1.6,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PreviewImage extends StatelessWidget {
  const _PreviewImage({required this.imageUrl});

  final String imageUrl;

  @override
  Widget build(BuildContext context) {
    if (imageUrl.isEmpty) {
      return _placeholder();
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.network(
        imageUrl,
        height: 180,
        width: double.infinity,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => _placeholder(),
      ),
    );
  }

  Widget _placeholder() {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          colors: <Color>[Color(0xFFFFF9F1), Color(0xFFF4F1EA)],
        ),
      ),
      child: const Center(
        child: Icon(
          Icons.inventory_2_outlined,
          size: 72,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 80,
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Map<String, dynamic> _buildPreviewPayload(ProductResult result) {
  if (result.normalizedProduct.isNotEmpty) {
    return result.normalizedProduct;
  }
  if (result.rawProduct.isNotEmpty) {
    return result.rawProduct;
  }
  return <String, dynamic>{
    'id': result.id,
    'title': result.name,
    'sku': result.sku,
    'price': result.price,
    'source': result.source,
  };
}

Map<String, dynamic> _sanitizePayload(Map<String, dynamic> payload) {
  return payload.map(
    (String key, dynamic value) => MapEntry<String, dynamic>(
      sanitizeDisplayText(key),
      _sanitizeValue(value),
    ),
  );
}

dynamic _sanitizeValue(dynamic value) {
  if (value is String) {
    return sanitizeDisplayText(value);
  }
  if (value is List) {
    return value.map(_sanitizeValue).toList();
  }
  if (value is Map) {
    return value.map(
      (dynamic key, dynamic innerValue) => MapEntry<dynamic, dynamic>(
        sanitizeDisplayText(key.toString()),
        _sanitizeValue(innerValue),
      ),
    );
  }
  return value;
}

String _firstImage(ProductResult result) {
  final normalizedImages = result.normalizedProduct['images'];
  if (normalizedImages is List && normalizedImages.isNotEmpty) {
    return normalizedImages.first.toString();
  }
  final rawImages = result.rawProduct['images'];
  if (rawImages is List && rawImages.isNotEmpty) {
    return rawImages.first.toString();
  }
  return '';
}

String _resolveFolderPath(ProductResult result) {
  final preferredPath = result.exportFilePath.isNotEmpty
      ? result.exportFilePath
      : result.normalizedFilePath.isNotEmpty
      ? result.normalizedFilePath
      : result.rawFilePath;
  if (preferredPath.isEmpty) {
    return '';
  }
  return File(preferredPath).parent.path;
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

Future<void> _openFolder(String folderPath) async {
  if (folderPath.isEmpty) {
    return;
  }
  final directory = Directory(folderPath);
  if (!directory.existsSync()) {
    return;
  }
  if (Platform.isWindows) {
    await Process.start('explorer.exe', <String>[folderPath]);
    return;
  }
  await Process.start(folderPath, const <String>[]);
}

String _statusLabel(String status) {
  switch (status.trim().toLowerCase()) {
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
