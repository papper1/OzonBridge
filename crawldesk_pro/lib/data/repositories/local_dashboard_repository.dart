import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import '../models/crawl_job.dart';
import '../models/dashboard_snapshot.dart';
import '../models/dashboard_summary.dart';

final localDashboardRepositoryProvider = Provider<LocalDashboardRepository>(
  (ref) => const LocalDashboardRepository(),
);

final localDashboardSnapshotProvider = StreamProvider<DashboardSnapshot>((
  ref,
) async* {
  final repository = ref.watch(localDashboardRepositoryProvider);
  yield await repository.loadSnapshot();
  yield* Stream<Duration>.periodic(
    const Duration(seconds: 5),
    (int tick) => Duration(seconds: tick),
  ).asyncMap((_) => repository.loadSnapshot());
});

class LocalDashboardRepository {
  const LocalDashboardRepository();

  Future<DashboardSnapshot> loadSnapshot() async {
    final summary = await _loadSummary();
    final jobs = await _loadJobs();
    return DashboardSnapshot(summary: summary, jobs: jobs);
  }

  Future<DashboardSummary> _loadSummary() async {
    final payload = await _readJsonMap(_resolvePath('dashboard_summary.json'));
    if (payload.isEmpty) {
      return const DashboardSummary.empty();
    }
    return DashboardSummary.fromJson(payload);
  }

  Future<List<CrawlJob>> _loadJobs() async {
    final payload = await _readJsonMap(_resolvePath('recent_jobs.json'));
    final items = payload['items'];
    if (items is! List) {
      return const <CrawlJob>[];
    }
    return items
        .whereType<Map>()
        .map(
          (Map item) => CrawlJob.fromJson(
            item.map(
              (dynamic key, dynamic value) => MapEntry(key.toString(), value),
            ),
          ),
        )
        .toList();
  }

  Future<Map<String, dynamic>> _readJsonMap(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      return const <String, dynamic>{};
    }
    try {
      final text = await file.readAsString();
      final payload = jsonDecode(text);
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

  String _resolvePath(String fileName) {
    return File('${AppConfig.localAppDataDir}/$fileName').absolute.path;
  }
}
