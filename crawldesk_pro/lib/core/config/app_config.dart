import 'dart:io';

class AppConfig {
  static const String _backendBaseUrlOverride = String.fromEnvironment(
    'BACKEND_BASE_URL',
    defaultValue: '',
  );
  static const String _localAppDataDirOverride = String.fromEnvironment(
    'LOCAL_APP_DATA_DIR',
    defaultValue: '',
  );
  static const String backendHost = String.fromEnvironment(
    'BACKEND_HOST',
    defaultValue: '127.0.0.1',
  );
  static const int backendPort = int.fromEnvironment(
    'BACKEND_PORT',
    defaultValue: 8000,
  );
  static const String appFolderName = 'CrawlDesk Pro';

  static String get backendBaseUrl =>
      _backendBaseUrlOverride.isNotEmpty
      ? _backendBaseUrlOverride
      : 'http://$backendHost:$backendPort';

  static String get executableDir =>
      File(Platform.resolvedExecutable).parent.absolute.path;

  static String get installRootDir => executableDir;

  static String get bundledRuntimeDir =>
      Directory('$installRootDir/runtime').absolute.path;

  static String get bundledBackendDir =>
      Directory('$bundledRuntimeDir/backend').absolute.path;

  static String get bundledBackendExecutablePath =>
      File('$bundledBackendDir/crawldesk_backend.exe').absolute.path;

  static String get bundledPlaywrightDir =>
      Directory('$bundledRuntimeDir/ms-playwright').absolute.path;

  static String get bundledTemplatesDir =>
      Directory('$bundledRuntimeDir/templates').absolute.path;

  static String get bundledAssetsTemplatesDir =>
      Directory('$bundledRuntimeDir/assets/templates').absolute.path;

  static String get localWorkspaceDir {
    final localAppData = Platform.environment['LOCALAPPDATA'] ?? '';
    if (localAppData.isNotEmpty) {
      return Directory('$localAppData/$appFolderName').absolute.path;
    }
    return Directory('$installRootDir/user_data').absolute.path;
  }

  static String get localDataRootDir =>
      Directory('$localWorkspaceDir/data').absolute.path;

  static String get localAppDataDir =>
      _localAppDataDirOverride.isNotEmpty
      ? Directory(_localAppDataDirOverride).absolute.path
      : Directory('$localDataRootDir/app').absolute.path;

  static String get localRawDataDir =>
      Directory('$localDataRootDir/raw').absolute.path;

  static String get localCleanDataDir =>
      Directory('$localDataRootDir/clean').absolute.path;

  static String get localExportDir =>
      Directory('$localDataRootDir/export').absolute.path;

  static String get localLogDir =>
      Directory('$localDataRootDir/logs').absolute.path;

  static String get backendStartupLogPath =>
      File('$localLogDir/backend_startup.log').absolute.path;

  static String get localTemplatesDir =>
      Directory('$localWorkspaceDir/templates').absolute.path;

  static String get localAssetsTemplatesDir =>
      Directory('$localWorkspaceDir/assets/templates').absolute.path;

  static String get devBackendProjectDir {
    final candidates = <String>[
      Directory('${Directory.current.path}/../1688_to_ozon').absolute.path,
      Directory('${Directory.current.path}/1688_to_ozon').absolute.path,
      Directory('$installRootDir/../1688_to_ozon').absolute.path,
    ];
    for (final candidate in candidates) {
      if (Directory(candidate).existsSync()) {
        return candidate;
      }
    }
    return candidates.first;
  }

  static String get devTemplatesDir =>
      Directory('$devBackendProjectDir/templates').absolute.path;

  static String get devAssetsTemplatesDir =>
      Directory('$devBackendProjectDir/assets/templates').absolute.path;

  static bool get isPackagedBackendAvailable =>
      File(bundledBackendExecutablePath).existsSync();

  static String resolveUrl(String pathOrUrl) {
    if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
      return pathOrUrl;
    }
    final normalizedBase = backendBaseUrl.endsWith('/')
        ? backendBaseUrl.substring(0, backendBaseUrl.length - 1)
        : backendBaseUrl;
    final normalizedPath = pathOrUrl.startsWith('/') ? pathOrUrl : '/$pathOrUrl';
    return '$normalizedBase$normalizedPath';
  }

  static Duration get connectTimeout => const Duration(seconds: 15);
  static Duration get receiveTimeout => const Duration(seconds: 60);
}
