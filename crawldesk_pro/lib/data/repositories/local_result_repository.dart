import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import '../models/product_result.dart';

final localResultRepositoryProvider = Provider<LocalResultRepository>(
  (ref) => const LocalResultRepository(),
);

final localResultsProvider = StreamProvider<List<ProductResult>>((ref) async* {
  final repository = ref.watch(localResultRepositoryProvider);
  yield await repository.loadResults();
  yield* Stream<Duration>.periodic(
    const Duration(seconds: 5),
    (int tick) => Duration(seconds: tick),
  ).asyncMap((_) => repository.loadResults());
});

class LocalResultRepository {
  const LocalResultRepository();

  Future<List<ProductResult>> loadResults() async {
    final jobHistory = await _readJsonList(_appDataPath('job_history.json'));
    final fromHistory = _parseJobHistory(jobHistory);
    if (fromHistory.isNotEmpty) {
      return fromHistory;
    }
    return _loadFromCleanFiles();
  }

  List<ProductResult> _parseJobHistory(List<Map<String, dynamic>> history) {
    final results = <ProductResult>[];
    for (final record in history) {
      final result = _asMap(record['result']);
      final export = _asMap(result['export']);
      final exportFileName = (export['file_name'] ?? '').toString();
      final exportFilePath = exportFileName.isEmpty ? '' : _dataPath('export/$exportFileName');
      final items = result['items'];
      if (items is! List) {
        continue;
      }
      for (final item in items.whereType<Map>()) {
        final itemMap = item.map(
          (dynamic key, dynamic value) => MapEntry(key.toString(), value),
        );
        results.add(
          ProductResult.fromJson(itemMap).copyWith(
            rawFilePath: (itemMap['raw_file_path'] ?? '').toString(),
            normalizedFilePath: (itemMap['normalized_file_path'] ?? '').toString(),
            exportFilePath: exportFilePath,
          ),
        );
      }
    }
    results.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return results;
  }

  Future<List<ProductResult>> _loadFromCleanFiles() async {
    final cleanDirectory = Directory(_dataPath('clean'));
    if (!await cleanDirectory.exists()) {
      return const <ProductResult>[];
    }

    final files = await cleanDirectory
        .list()
        .where((FileSystemEntity entity) => entity is File && entity.path.endsWith('.json'))
        .cast<File>()
        .toList();

    final records = <_CleanFileRecord>[];
    for (final file in files) {
      final payload = await _readJsonMap(file.path);
      if (payload.isEmpty) {
        continue;
      }
      final stat = await file.stat();
      records.add(_CleanFileRecord(file: file, payload: payload, modifiedAt: stat.modified));
    }

    records.sort((a, b) => b.modifiedAt.compareTo(a.modifiedAt));
    return records.asMap().entries.map((entry) {
      final index = entry.key + 1;
      final record = entry.value;
      final payload = record.payload;
      final rawProduct = _loadRawPair(record.file.path);
      final title = _pickFirstString(
        <dynamic>[
          payload['translated_title'],
          payload['title'],
          payload['product_name'],
        ],
      );
      final price = _pickFirstString(
        <dynamic>[payload['price'], rawProduct['price']],
      );
      final sku = _extractSku(payload, rawProduct, index);
      final translated = _pickFirstString(<dynamic>[payload['translated_title']]).isNotEmpty;

      return ProductResult(
        id: 'LOCAL-${index.toString().padLeft(3, '0')}',
        source: _pickFirstString(<dynamic>[payload['source'], payload['supplier'], 'local']),
        name: title.isEmpty ? 'Sản phẩm $index' : title,
        sku: sku,
        price: price.isEmpty ? '-' : price,
        status: translated ? 'success' : 'pending',
        mapping: payload.isNotEmpty ? 100 : 0,
        translation: translated ? 100 : 0,
        exported: false,
        updatedAt: record.modifiedAt.toLocal().toString(),
        productCount: _extractProductCount(payload),
        productUrl: _pickFirstString(<dynamic>[payload['product_url'], payload['source_url']]),
        rawFilePath: _dataPath('raw/${record.file.uri.pathSegments.last}'),
        normalizedFilePath: record.file.path,
        exportFilePath: _findLatestExportPath(
          _pickFirstString(<dynamic>[payload['source'], payload['supplier'], '']),
        ),
        rawProduct: rawProduct,
        normalizedProduct: payload,
        mappedProduct: const <String, dynamic>{},
      );
    }).toList();
  }

  Map<String, dynamic> _loadRawPair(String cleanFilePath) {
    final fileName = cleanFilePath.split(Platform.pathSeparator).last;
    return _readJsonMapSync(_dataPath('raw/$fileName'));
  }

  Future<List<Map<String, dynamic>>> _readJsonList(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      return const <Map<String, dynamic>>[];
    }
    try {
      final payload = jsonDecode(await file.readAsString());
      if (payload is! List) {
        return const <Map<String, dynamic>>[];
      }
      return payload.whereType<Map>().map(
        (Map item) => item.map(
          (dynamic key, dynamic value) => MapEntry(key.toString(), value),
        ),
      ).toList();
    } on FileSystemException {
      return const <Map<String, dynamic>>[];
    } on FormatException {
      return const <Map<String, dynamic>>[];
    }
  }

  Future<Map<String, dynamic>> _readJsonMap(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      return const <String, dynamic>{};
    }
    try {
      final payload = jsonDecode(await file.readAsString());
      return _asMap(payload);
    } on FileSystemException {
      return const <String, dynamic>{};
    } on FormatException {
      return const <String, dynamic>{};
    }
  }

  Map<String, dynamic> _readJsonMapSync(String path) {
    final file = File(path);
    if (!file.existsSync()) {
      return const <String, dynamic>{};
    }
    try {
      final payload = jsonDecode(file.readAsStringSync());
      return _asMap(payload);
    } on FileSystemException {
      return const <String, dynamic>{};
    } on FormatException {
      return const <String, dynamic>{};
    }
  }

  String _appDataPath(String fileName) {
    return File('${AppConfig.localAppDataDir}/$fileName').absolute.path;
  }

  String _dataPath(String relativePath) {
    return File('${AppConfig.localDataRootDir}/$relativePath').absolute.path;
  }

  String _findLatestExportPath(String source) {
    final directory = Directory(_dataPath('export'));
    if (!directory.existsSync()) {
      return '';
    }
    final normalizedSource = source.trim().toLowerCase();
    final files = directory
        .listSync()
        .whereType<File>()
        .where((File file) => file.path.toLowerCase().endsWith('.xlsx'))
        .toList();
    files.sort((a, b) => b.statSync().modified.compareTo(a.statSync().modified));
    for (final file in files) {
      if (normalizedSource.isNotEmpty &&
          file.path.toLowerCase().contains(normalizedSource)) {
        return file.path;
      }
    }
    return files.isNotEmpty ? files.first.path : '';
  }
}

class _CleanFileRecord {
  const _CleanFileRecord({
    required this.file,
    required this.payload,
    required this.modifiedAt,
  });

  final File file;
  final Map<String, dynamic> payload;
  final DateTime modifiedAt;
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (dynamic key, dynamic value) => MapEntry(key.toString(), value),
    );
  }
  return const <String, dynamic>{};
}

String _pickFirstString(List<dynamic> values) {
  for (final value in values) {
    final text = value?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return '';
}

String _extractSku(
  Map<String, dynamic> normalized,
  Map<String, dynamic> raw,
  int index,
) {
  final skuMap = _asMap(normalized['sku']);
  return _pickFirstString(<dynamic>[
    normalized['model'],
    normalized['sku'],
    skuMap['product_id'],
    skuMap['raw_text'],
    raw['model'],
    'ITEM-${index.toString().padLeft(3, '0')}',
  ]);
}

int _extractProductCount(Map<String, dynamic> payload) {
  final variants = payload['variants'];
  if (variants is List && variants.isNotEmpty) {
    return variants.length;
  }
  return 1;
}
