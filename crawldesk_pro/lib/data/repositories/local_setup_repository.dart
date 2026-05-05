import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import '../models/session_auth_status.dart';
import '../models/setup_status.dart';
import 'crawl_repository.dart';
import '../services/crawl_api_service.dart';

final localSetupRepositoryProvider = Provider<LocalSetupRepository>(
  (ref) => const LocalSetupRepository(),
);

final localSetupStatusProvider = FutureProvider<SetupStatus>((ref) async {
  final repository = ref.watch(localSetupRepositoryProvider);
  final apiService = ref.watch(crawlApiServiceProvider);
  return repository.loadStatus(apiService);
});

class LocalSetupRepository {
  const LocalSetupRepository();

  Future<SetupStatus> loadStatus(CrawlApiService apiService) async {
    await ensureEnvTemplate();
    final envValues = await loadEnvValues();

    SessionAuthStatus sessionStatus;
    try {
      sessionStatus = await apiService.get1688SessionStatus();
    } catch (_) {
      sessionStatus = SessionAuthStatus(
        exists: await File(_sessionFilePath).exists(),
        valid: false,
        flowActive: false,
        sessionPath: _sessionFilePath,
        message: 'Backend chưa sẵn sàng để kiểm tra session 1688.',
      );
    }

    return SetupStatus(
      envFileExists: await File(_envFilePath).exists(),
      zyteApiKeyConfigured:
          (envValues['ZYTE_API_KEY'] ?? '').trim().isNotEmpty,
      openAiApiKeyConfigured:
          (envValues['OPENAI_API_KEY'] ?? '').trim().isNotEmpty,
      openAiModel:
          (envValues['OPENAI_MODEL'] ?? 'gpt-4.1-mini').trim(),
      sessionFileExists: sessionStatus.exists,
      sessionValid: sessionStatus.valid,
      sessionFlowActive: sessionStatus.flowActive,
      envFilePath: _envFilePath,
      sessionFilePath: sessionStatus.sessionPath.isEmpty
          ? _sessionFilePath
          : sessionStatus.sessionPath,
      sessionMessage: sessionStatus.message,
    );
  }

  Future<Map<String, String>> loadEnvValues() async {
    await ensureEnvTemplate();
    final file = File(_envFilePath);
    if (!await file.exists()) {
      return const <String, String>{};
    }

    final lines = const LineSplitter().convert(await file.readAsString());
    final values = <String, String>{};
    for (final line in lines) {
      final trimmed = line.trim();
      if (trimmed.isEmpty || trimmed.startsWith('#') || !trimmed.contains('=')) {
        continue;
      }
      final index = trimmed.indexOf('=');
      final key = trimmed.substring(0, index).trim();
      final value = trimmed.substring(index + 1).trim();
      values[key] = value;
    }
    return values;
  }

  Future<void> saveEnvValues({
    required String zyteApiKey,
    required String openAiApiKey,
    required String openAiModel,
  }) async {
    final file = File(_envFilePath);
    if (!await file.parent.exists()) {
      await file.parent.create(recursive: true);
    }
    final content = StringBuffer()
      ..writeln('# CrawlDesk Pro local runtime configuration')
      ..writeln('ZYTE_API_KEY=${zyteApiKey.trim()}')
      ..writeln('OPENAI_API_KEY=${openAiApiKey.trim()}')
      ..writeln('OPENAI_MODEL=${openAiModel.trim().isEmpty ? 'gpt-4.1-mini' : openAiModel.trim()}');
    await file.writeAsString(content.toString(), flush: true);
  }

  Future<void> ensureEnvTemplate() async {
    final file = File(_envFilePath);
    if (await file.exists()) {
      return;
    }
    if (!await file.parent.exists()) {
      await file.parent.create(recursive: true);
    }
    const template = '''
# CrawlDesk Pro local runtime configuration
ZYTE_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
''';
    await file.writeAsString(template.trimLeft(), flush: true);
  }

  Future<void> openEnvFile() => _openPath(_envFilePath);

  Future<void> openWorkspaceFolder() => _openFolder(AppConfig.localWorkspaceDir);

  Future<void> openSessionFolder() => _openFolder(Directory(_sessionFilePath).parent.path);

  Future<void> _openPath(String path) async {
    if (Platform.isWindows) {
      await Process.start('cmd', <String>['/c', 'start', '', path]);
      return;
    }
    await Process.start(path, const <String>[]);
  }

  Future<void> _openFolder(String folderPath) async {
    if (Platform.isWindows) {
      await Process.start('explorer.exe', <String>[folderPath]);
      return;
    }
    await Process.start(folderPath, const <String>[]);
  }

  String get _envFilePath => File('${AppConfig.localWorkspaceDir}/.env').absolute.path;

  String get _sessionFilePath =>
      File('${AppConfig.localDataRootDir}/session.json').absolute.path;
}
