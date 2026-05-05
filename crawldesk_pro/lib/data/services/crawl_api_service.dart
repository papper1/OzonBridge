import '../../core/config/app_config.dart';
import '../../core/network/api_client.dart';
import '../models/crawl_job.dart';
import '../models/crawl_request.dart';
import '../models/crawl_status.dart';
import '../models/export_result.dart';
import '../models/product_result.dart';
import '../models/session_auth_status.dart';

class CrawlApiService {
  const CrawlApiService(this._apiClient);

  final ApiClient _apiClient;

  Future<void> healthCheck() async {
    await _apiClient.getJson('/health');
  }

  Future<SessionAuthStatus> get1688SessionStatus() async {
    final response = await _apiClient.getJson('/auth/1688/status');
    return SessionAuthStatus.fromJson(response);
  }

  Future<SessionAuthStatus> open1688SessionFlow() async {
    final response = await _apiClient.postJson('/auth/1688/open');
    return SessionAuthStatus.fromJson(response);
  }

  Future<SessionAuthStatus> save1688Session() async {
    final response = await _apiClient.postJson('/auth/1688/save');
    return SessionAuthStatus.fromJson(response);
  }

  Future<CrawlJob> startCrawl(CrawlRequest request) async {
    final response = await _apiClient.postJson(
      '/crawl',
      data: request.toJson(),
    );
    return CrawlJob.fromJson(response);
  }

  Future<CrawlStatus> getStatus(String jobId) async {
    final response = await _apiClient.getJson('/crawl/status/$jobId');
    return CrawlStatus.fromJson(response);
  }

  Future<List<ProductResult>> getResult(String jobId) async {
    final response = await _apiClient.getJson('/crawl/result/$jobId');
    final result = _asMap(response['result']);
    if (result.isEmpty) {
      return const <ProductResult>[];
    }
    final items = result['items'];
    if (items is! List) {
      return const <ProductResult>[];
    }
    return items
        .whereType<Map>()
        .map(
          (Map item) => ProductResult.fromJson(
            item.map(
              (dynamic key, dynamic value) => MapEntry(key.toString(), value),
            ),
          ),
        )
        .toList();
  }

  Future<List<Map<String, dynamic>>> translate(
    List<Map<String, dynamic>> products,
  ) async {
    final response = await _apiClient.postJson(
      '/translate',
      data: <String, dynamic>{'products': products},
    );
    final items = response['items'];
    if (items is! List) {
      return const <Map<String, dynamic>>[];
    }
    return items
        .whereType<Map>()
        .map(
          (Map item) => item.map(
            (dynamic key, dynamic value) => MapEntry(key.toString(), value),
          ),
        )
        .toList();
  }

  Future<List<Map<String, dynamic>>> mapToOzon(
    List<Map<String, dynamic>> products,
  ) async {
    final response = await _apiClient.postJson(
      '/map-to-ozon',
      data: <String, dynamic>{'products': products},
    );
    final items = response['items'];
    if (items is! List) {
      return const <Map<String, dynamic>>[];
    }
    return items
        .whereType<Map>()
        .map(
          (Map item) => item.map(
            (dynamic key, dynamic value) => MapEntry(key.toString(), value),
          ),
        )
        .toList();
  }

  Future<ExportResult> export(List<Map<String, dynamic>> products) async {
    final response = await _apiClient.postJson(
      '/export',
      data: <String, dynamic>{'products': products},
    );
    final result = ExportResult.fromJson(response);
    return ExportResult(
      fileId: result.fileId,
      fileName: result.fileName,
      downloadUrl: AppConfig.resolveUrl(result.downloadUrl),
    );
  }
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
