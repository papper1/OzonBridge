import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../models/crawl_job.dart';
import '../models/crawl_request.dart';
import '../models/crawl_status.dart';
import '../models/export_result.dart';
import '../models/product_result.dart';
import '../services/crawl_api_service.dart';

final crawlApiServiceProvider = Provider<CrawlApiService>(
  (ref) => CrawlApiService(ref.watch(apiClientProvider)),
);

final crawlRepositoryProvider = Provider<CrawlRepository>(
  (ref) => CrawlRepository(ref.watch(crawlApiServiceProvider)),
);

class CrawlRepository {
  const CrawlRepository(this._apiService);

  final CrawlApiService _apiService;

  Future<void> healthCheck() => _apiService.healthCheck();

  Future<CrawlJob> startCrawl(CrawlRequest request) =>
      _apiService.startCrawl(request);

  Future<CrawlStatus> getStatus(String jobId) => _apiService.getStatus(jobId);

  Future<List<ProductResult>> getResult(String jobId) =>
      _apiService.getResult(jobId);

  Future<List<Map<String, dynamic>>> translate(
    List<Map<String, dynamic>> products,
  ) => _apiService.translate(products);

  Future<List<Map<String, dynamic>>> mapToOzon(
    List<Map<String, dynamic>> products,
  ) => _apiService.mapToOzon(products);

  Future<ExportResult> export(List<Map<String, dynamic>> products) =>
      _apiService.export(products);
}
