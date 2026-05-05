import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../config/app_config.dart';

class DesktopRuntime {
  DesktopRuntime._();

  static final DesktopRuntime instance = DesktopRuntime._();

  bool _isStartingBackend = false;

  Future<void> initialize() async {
    await _prepareLocalWorkspace();
    await ensureBackendStarted();
  }

  Future<void> ensureBackendStarted() async {
    if (_isStartingBackend) {
      return;
    }
    if (await _isBackendHealthy()) {
      return;
    }

    final startConfig = _resolveStartConfig();
    if (startConfig == null) {
      await _appendLog('No backend start configuration available.');
      return;
    }

    _isStartingBackend = true;
    try {
      await _appendLog('Starting backend: ${startConfig.executable}');
      final process = await Process.start(
        startConfig.executable,
        startConfig.arguments,
        workingDirectory: startConfig.workingDirectory,
        environment: startConfig.environment,
        mode: ProcessStartMode.normal,
        runInShell: false,
      );
      _pipeProcessLogs(process);
      final healthy = await _waitUntilHealthy(const Duration(seconds: 25));
      if (!healthy) {
        await _appendLog('Backend did not become healthy within timeout.');
      }
    } catch (error) {
      await _appendLog('Backend start failed: $error');
    } finally {
      _isStartingBackend = false;
    }
  }

  Future<void> _prepareLocalWorkspace() async {
    final directories = <Directory>[
      Directory(AppConfig.localWorkspaceDir),
      Directory(AppConfig.localDataRootDir),
      Directory(AppConfig.localAppDataDir),
      Directory(AppConfig.localRawDataDir),
      Directory(AppConfig.localCleanDataDir),
      Directory(AppConfig.localExportDir),
      Directory(AppConfig.localLogDir),
      Directory(AppConfig.localTemplatesDir),
      Directory(AppConfig.localAssetsTemplatesDir),
    ];

    for (final directory in directories) {
      if (!await directory.exists()) {
        await directory.create(recursive: true);
      }
    }

    await _copySeedFiles(
      sourceDir: _seedTemplatesDir,
      targetDir: AppConfig.localTemplatesDir,
      predicate: (String path) => path.endsWith('.json'),
    );
    await _copySeedFiles(
      sourceDir: _seedAssetsTemplatesDir,
      targetDir: AppConfig.localAssetsTemplatesDir,
      predicate: (String path) => path.endsWith('.xlsx'),
    );
  }

  Future<void> _copySeedFiles({
    required String sourceDir,
    required String targetDir,
    required bool Function(String path) predicate,
  }) async {
    final source = Directory(sourceDir);
    if (!await source.exists()) {
      return;
    }

    await for (final entity in source.list(recursive: false)) {
      if (entity is! File || !predicate(entity.path)) {
        continue;
      }
      final fileName = entity.uri.pathSegments.last;
      final destination = File('$targetDir/$fileName');
      if (await destination.exists()) {
        continue;
      }
      await entity.copy(destination.path);
    }
  }

  Future<bool> _isBackendHealthy() async {
    final client = HttpClient()..connectionTimeout = AppConfig.connectTimeout;
    try {
      final request = await client.getUrl(
        Uri.parse('${AppConfig.backendBaseUrl}/health'),
      );
      final response = await request.close();
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    } finally {
      client.close(force: true);
    }
  }

  Future<bool> _waitUntilHealthy(Duration timeout) async {
    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      if (await _isBackendHealthy()) {
        await _appendLog('Backend is healthy at ${AppConfig.backendBaseUrl}.');
        return true;
      }
      await Future<void>.delayed(const Duration(milliseconds: 500));
    }
    return false;
  }

  _BackendStartConfig? _resolveStartConfig() {
    final environment = <String, String>{
      ...Platform.environment,
      'CRAWLDESK_HOST': AppConfig.backendHost,
      'CRAWLDESK_PORT': '${AppConfig.backendPort}',
      'CRAWLDESK_DATA_DIR': AppConfig.localDataRootDir,
      'CRAWLDESK_RESOURCE_ROOT': AppConfig.localWorkspaceDir,
      'CRAWLDESK_TEMPLATES_DIR': AppConfig.localTemplatesDir,
      'CRAWLDESK_ASSETS_TEMPLATES_DIR': AppConfig.localAssetsTemplatesDir,
    };

    if (Directory(AppConfig.bundledPlaywrightDir).existsSync()) {
      environment['PLAYWRIGHT_BROWSERS_PATH'] = AppConfig.bundledPlaywrightDir;
    }

    if (AppConfig.isPackagedBackendAvailable) {
      return _BackendStartConfig(
        executable: AppConfig.bundledBackendExecutablePath,
        arguments: const <String>[],
        workingDirectory: AppConfig.bundledBackendDir,
        environment: environment,
      );
    }

    if (File('${AppConfig.devBackendProjectDir}/backend/api/main.py').existsSync()) {
      return _BackendStartConfig(
        executable: 'python',
        arguments: <String>[
          '-m',
          'uvicorn',
          'backend.api.main:app',
          '--host',
          AppConfig.backendHost,
          '--port',
          '${AppConfig.backendPort}',
        ],
        workingDirectory: AppConfig.devBackendProjectDir,
        environment: environment,
      );
    }

    return null;
  }

  void _pipeProcessLogs(Process process) {
    process.stdout
        .transform(utf8.decoder)
        .listen((chunk) => unawaited(_appendLog(chunk.trimRight())));
    process.stderr
        .transform(utf8.decoder)
        .listen((chunk) => unawaited(_appendLog(chunk.trimRight())));
    unawaited(
      process.exitCode.then(
        (code) => _appendLog('Backend process exited with code $code.'),
      ),
    );
  }

  Future<void> _appendLog(String message) async {
    final text = message.trim();
    if (text.isEmpty) {
      return;
    }
    final file = File(AppConfig.backendStartupLogPath);
    if (!await file.parent.exists()) {
      await file.parent.create(recursive: true);
    }
    final line = '[${DateTime.now().toIso8601String()}] $text\n';
    await file.writeAsString(line, mode: FileMode.append, flush: true);
  }

  String get _seedTemplatesDir =>
      AppConfig.isPackagedBackendAvailable
      ? AppConfig.bundledTemplatesDir
      : AppConfig.devTemplatesDir;

  String get _seedAssetsTemplatesDir =>
      AppConfig.isPackagedBackendAvailable
      ? AppConfig.bundledAssetsTemplatesDir
      : AppConfig.devAssetsTemplatesDir;
}

class _BackendStartConfig {
  const _BackendStartConfig({
    required this.executable,
    required this.arguments,
    required this.workingDirectory,
    required this.environment,
  });

  final String executable;
  final List<String> arguments;
  final String workingDirectory;
  final Map<String, String> environment;
}
