import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import '../models/ozon_template.dart';

final localTemplateRepositoryProvider = Provider<LocalTemplateRepository>(
  (ref) => const LocalTemplateRepository(),
);

final localTemplatesProvider = FutureProvider<List<OzonTemplate>>((ref) async {
  return ref.watch(localTemplateRepositoryProvider).loadTemplates();
});

class LocalTemplateRepository {
  const LocalTemplateRepository();

  Future<List<OzonTemplate>> loadTemplates() async {
    final directory = Directory(_templatesDirPath);
    if (!await directory.exists()) {
      return const <OzonTemplate>[];
    }

    final files = await directory
        .list()
        .where(
          (FileSystemEntity entity) =>
              entity is File &&
              entity.path.endsWith('.json') &&
              !entity.path.endsWith('template_mapping.json'),
        )
        .cast<File>()
        .toList();

    final templates = <OzonTemplate>[];
    for (final file in files) {
      final payload = await _readJson(file);
      if (payload.isEmpty) {
        continue;
      }
      templates.add(_toTemplate(file.path, payload));
    }
    templates.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return templates;
  }

  Future<void> createTemplate({
    required String name,
    required String category,
    required String version,
    required String status,
    required String sourceWorkbookPath,
    required String baseTemplateKey,
    required List<String> requiredFields,
    required String sheetName,
    required int headerRow,
    required int dataStartRow,
  }) async {
    final slug = _slugify(name);
    final templatePath = File('$_templatesDirPath/$slug.json');
    if (await templatePath.exists()) {
      throw StateError('Template đã tồn tại: $name');
    }

    final basePayload = await _loadBasePayload(baseTemplateKey);
    final relativeWorkbookPath = sourceWorkbookPath.trim().isEmpty
        ? (basePayload['workbook_template'] ?? '').toString()
        : _toRelativeWorkbookPath(await _copyWorkbook(sourceWorkbookPath));

    final payload = <String, dynamic>{
      ...basePayload,
      'template_name': slug,
      'display_name': name,
      'category': category,
      'version': version,
      'status': status,
      'required_fields': requiredFields,
      'workbook_template': relativeWorkbookPath,
      'sheet_name': sheetName,
      'header_row': headerRow,
      'data_start_row': dataStartRow,
    };

    await _writeJson(templatePath, payload);
  }

  Future<void> updateTemplate({
    required OzonTemplate template,
    required String name,
    required String category,
    required String version,
    required String status,
    required String sourceWorkbookPath,
    required List<String> requiredFields,
    required String sheetName,
    required int headerRow,
    required int dataStartRow,
  }) async {
    final payload = await _readJson(File(template.jsonFilePath));
    if (payload.isEmpty) {
      throw StateError('Không đọc được file template hiện tại.');
    }

    String workbookPath = template.workbookAbsolutePath;
    if (sourceWorkbookPath.trim().isNotEmpty &&
        sourceWorkbookPath.trim() != template.workbookAbsolutePath) {
      workbookPath = await _copyWorkbook(sourceWorkbookPath);
    }

    final updated = <String, dynamic>{
      ...payload,
      'display_name': name,
      'category': category,
      'version': version,
      'status': status,
      'required_fields': requiredFields,
      'workbook_template': workbookPath.isEmpty
          ? template.workbookTemplate
          : _toRelativeWorkbookPath(workbookPath),
      'sheet_name': sheetName,
      'header_row': headerRow,
      'data_start_row': dataStartRow,
    };

    await _writeJson(File(template.jsonFilePath), updated);
  }

  Future<void> deleteTemplate(OzonTemplate template) async {
    final jsonFile = File(template.jsonFilePath);
    if (await jsonFile.exists()) {
      await jsonFile.delete();
    }

    final workbookFile = File(template.workbookAbsolutePath);
    if (await workbookFile.exists()) {
      final templates = await loadTemplates();
      final stillReferenced = templates.any(
        (OzonTemplate item) =>
            item.key != template.key &&
            item.workbookAbsolutePath == template.workbookAbsolutePath,
      );
      if (!stillReferenced &&
          workbookFile.path.startsWith(_assetsTemplatesDirPath)) {
        await workbookFile.delete();
      }
    }
  }

  String get templatesDirPath => _templatesDirPath;
  String get assetsTemplatesDirPath => _assetsTemplatesDirPath;

  Future<Map<String, dynamic>> _loadBasePayload(String baseTemplateKey) async {
    final path = File('$_templatesDirPath/$baseTemplateKey.json');
    final payload = await _readJson(path);
    if (payload.isEmpty) {
      throw StateError('Không tìm thấy base template: $baseTemplateKey');
    }
    return payload;
  }

  OzonTemplate _toTemplate(String jsonFilePath, Map<String, dynamic> payload) {
    final templateKey = (payload['template_name'] ?? '').toString();
    final workbookTemplate = (payload['workbook_template'] ?? '').toString();
    final workbookAbsolutePath = _resolveWorkbookAbsolutePath(workbookTemplate);
    final requiredFields = _toStringList(payload['required_fields']);
    final fieldMap = payload['field_map'];
    final fieldMapKeys = fieldMap is Map
        ? fieldMap.keys.map((dynamic key) => key.toString()).toList()
        : const <String>[];
    final fileName = workbookTemplate.split('/').last;

    return OzonTemplate(
      key: templateKey,
      name: (payload['display_name'] ?? templateKey).toString(),
      category: (payload['category'] ?? 'Chưa phân loại').toString(),
      version: (payload['version'] ?? 'v1.0').toString(),
      fieldCount: fieldMapKeys.length,
      requiredFieldCount: requiredFields.length,
      status: (payload['status'] ?? 'Đồng bộ').toString(),
      fileName: fileName,
      requiredFields: requiredFields,
      jsonFilePath: jsonFilePath,
      workbookTemplate: workbookTemplate,
      workbookAbsolutePath: workbookAbsolutePath,
      fieldMapKeys: fieldMapKeys,
      sheetName: (payload['sheet_name'] ?? 'Template').toString(),
      headerRow: _asInt(payload['header_row'], 1),
      dataStartRow: _asInt(payload['data_start_row'], 2),
    );
  }

  Future<String> _copyWorkbook(String sourceWorkbookPath) async {
    final sourceFile = File(sourceWorkbookPath.trim());
    if (!await sourceFile.exists()) {
      throw StateError('Không tìm thấy file template: ${sourceFile.path}');
    }

    final destinationDirectory = Directory(_assetsTemplatesDirPath);
    if (!await destinationDirectory.exists()) {
      await destinationDirectory.create(recursive: true);
    }

    final fileName = sourceFile.uri.pathSegments.last;
    final destination = File('${destinationDirectory.path}/$fileName');
    await sourceFile.copy(destination.path);
    return destination.path;
  }

  String _resolveWorkbookAbsolutePath(String workbookTemplate) {
    if (workbookTemplate.isEmpty) {
      return '';
    }
    final normalized = workbookTemplate.replaceAll('/', Platform.pathSeparator);
    return File('${AppConfig.localWorkspaceDir}/$normalized').absolute.path;
  }

  String _toRelativeWorkbookPath(String absolutePath) {
    final assetsPath = Directory(_assetsTemplatesDirPath).absolute.path;
    final normalizedAbsolute = File(absolutePath).absolute.path;
    if (normalizedAbsolute.startsWith(assetsPath)) {
      final relativeName = normalizedAbsolute.substring(assetsPath.length).replaceAll('\\', '/');
      final trimmed = relativeName.startsWith('/') ? relativeName.substring(1) : relativeName;
      return 'assets/templates/$trimmed';
    }
    final fileName = File(absolutePath).uri.pathSegments.last;
    return 'assets/templates/$fileName';
  }

  Future<Map<String, dynamic>> _readJson(File file) async {
    if (!await file.exists()) {
      return const <String, dynamic>{};
    }
    try {
      final payload = jsonDecode(await file.readAsString());
      if (payload is Map<String, dynamic>) {
        return payload;
      }
      if (payload is Map) {
        return payload.map(
          (dynamic key, dynamic value) => MapEntry(key.toString(), value),
        );
      }
    } on FileSystemException {
      return const <String, dynamic>{};
    } on FormatException {
      return const <String, dynamic>{};
    }
    return const <String, dynamic>{};
  }

  Future<void> _writeJson(File file, Map<String, dynamic> payload) async {
    if (!await file.parent.exists()) {
      await file.parent.create(recursive: true);
    }
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(payload),
    );
  }

  List<String> _toStringList(dynamic value) {
    if (value is List) {
      return value.map((dynamic item) => item.toString()).toList();
    }
    return const <String>[];
  }

  int _asInt(dynamic value, int fallback) {
    if (value is int) {
      return value;
    }
    if (value is double) {
      return value.round();
    }
    return int.tryParse(value?.toString() ?? '') ?? fallback;
  }

  String _slugify(String text) {
    final cleaned = text.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '_');
    return cleaned.replaceAll(RegExp(r'^_+|_+$'), '');
  }

  String get _templatesDirPath =>
      Directory(AppConfig.localTemplatesDir).absolute.path;

  String get _assetsTemplatesDirPath =>
      Directory(AppConfig.localAssetsTemplatesDir).absolute.path;
}
