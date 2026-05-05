import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../../core/runtime/desktop_runtime.dart';
import '../../data/models/crawl_request.dart';
import '../../data/models/product_result.dart';
import '../../data/repositories/crawl_repository.dart';
import 'crawl_state.dart';

final crawlControllerProvider = NotifierProvider<CrawlController, CrawlState>(
  CrawlController.new,
);

class CrawlController extends Notifier<CrawlState> {
  Timer? _pollTimer;

  @override
  CrawlState build() {
    ref.onDispose(_stopPolling);
    Future<void>.microtask(_ensureBackendChecked);
    return const CrawlState();
  }

  void setTab(String tab) => state = state.copyWith(tab: tab);
  void setSource(String source) => state = state.copyWith(source: source);
  void setMode(String mode) => state = state.copyWith(mode: mode);
  void setTemplate(String template) =>
      state = state.copyWith(template: template);
  void setThreads(double value) =>
      state = state.copyWith(concurrentThreads: value);
  void setUseProxy(bool value) => state = state.copyWith(useProxy: value);
  void setTranslate(bool value) =>
      state = state.copyWith(translateToRussian: value);
  void setExportExcel(bool value) => state = state.copyWith(exportExcel: value);
  void setInput(String value) => state = state.copyWith(input: value);

  Future<void> _ensureBackendChecked() async {
    if (state.didCheckBackend || state.isCheckingBackend) {
      return;
    }
    await checkBackend();
  }

  Future<void> checkBackend() async {
    state = state.copyWith(
      didCheckBackend: true,
      isCheckingBackend: true,
      backendMessage: 'Đang kiểm tra backend...',
      clearErrorMessage: true,
    );

    try {
      await ref.read(crawlRepositoryProvider).healthCheck();
      state = state.copyWith(
        isCheckingBackend: false,
        backendAvailable: true,
        backendMessage: 'Backend đang hoạt động',
      );
      return;
    } on ApiException catch (error) {
      await DesktopRuntime.instance.ensureBackendStarted();
      try {
        await ref.read(crawlRepositoryProvider).healthCheck();
        state = state.copyWith(
          isCheckingBackend: false,
          backendAvailable: true,
          backendMessage: 'Backend đang hoạt động',
        );
        return;
      } on ApiException {
        state = state.copyWith(
          isCheckingBackend: false,
          backendAvailable: false,
          backendMessage: error.message,
          errorMessage: error.message,
        );
        return;
      }
    } catch (_) {
      await DesktopRuntime.instance.ensureBackendStarted();
      try {
        await ref.read(crawlRepositoryProvider).healthCheck();
        state = state.copyWith(
          isCheckingBackend: false,
          backendAvailable: true,
          backendMessage: 'Backend đang hoạt động',
        );
        return;
      } catch (_) {
        state = state.copyWith(
          isCheckingBackend: false,
          backendAvailable: false,
          backendMessage: 'Không thể kết nối backend',
          errorMessage: 'Không thể kết nối backend',
        );
      }
    }
  }

  Future<void> startCrawl() async {
    if (state.input.trim().isEmpty) {
      state = state.copyWith(
        errorMessage: 'Vui lòng nhập URL, keyword hoặc shop URL.',
      );
      return;
    }
    if (!state.backendAvailable) {
      await checkBackend();
      if (!state.backendAvailable) {
        return;
      }
    }

    state = state.copyWith(
      isSubmitting: true,
      jobMessage: 'Đang gửi yêu cầu crawl...',
      activeJobStatus: 'pending',
      clearErrorMessage: true,
      clearExportResult: true,
      liveResults: const <ProductResult>[],
      processed: 0,
      total: 0,
      stage: '',
    );

    try {
      final request = _buildRequest();
      final job = await ref.read(crawlRepositoryProvider).startCrawl(request);
      state = state.copyWith(
        isSubmitting: false,
        isPolling: true,
        activeJobId: job.id,
        activeJobStatus: job.status,
        jobMessage: job.message,
      );
      _startPolling(job.id);
    } on ApiException catch (error) {
      state = state.copyWith(
        isSubmitting: false,
        isPolling: false,
        errorMessage: error.message,
        jobMessage: error.message,
      );
    }
  }

  CrawlRequest _buildRequest() {
    final trimmedInput = state.input.trim();
    final lines = trimmedInput
        .split('\n')
        .where((String line) => line.trim().isNotEmpty)
        .toList();
    final primaryValue = lines.isEmpty ? '' : lines.first.trim();

    return CrawlRequest(
      platform: state.source.toLowerCase(),
      keyword: state.tab == 'Từ khóa' ? primaryValue : null,
      productUrl: state.tab == 'URL sản phẩm' ? primaryValue : null,
      shopUrl: state.tab == 'Theo shop' ? primaryValue : null,
      inputMode: state.tab == 'Từ khóa'
          ? 'keyword'
          : state.tab == 'Theo shop'
          ? 'shop_url'
          : 'product_url',
      maxLinks: state.inputCount > 0 ? state.inputCount : 1,
      translateToRussian: state.translateToRussian,
      mapToOzon: true,
      exportExcel: state.exportExcel,
      templateName: state.template,
    );
  }

  void _startPolling(String jobId) {
    _stopPolling();
    unawaited(_pollJob(jobId));
    _pollTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => unawaited(_pollJob(jobId)),
    );
  }

  void _stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  Future<void> _pollJob(String jobId) async {
    try {
      final status = await ref.read(crawlRepositoryProvider).getStatus(jobId);
      final partialResults = await ref
          .read(crawlRepositoryProvider)
          .getResult(jobId);

      state = state.copyWith(
        activeJobStatus: status.status,
        jobMessage: status.message,
        processed: status.processed,
        total: status.total,
        stage: status.stage,
        liveResults: partialResults.isNotEmpty
            ? partialResults
            : state.liveResults,
      );

      if (status.status == 'success') {
        _stopPolling();
        state = state.copyWith(
          isPolling: false,
          liveResults: partialResults.isNotEmpty
              ? partialResults
              : state.liveResults,
          activeJobStatus: 'success',
          jobMessage: status.message.isEmpty
              ? 'Crawl hoàn tất'
              : status.message,
        );
      } else if (status.status == 'failed') {
        _stopPolling();
        state = state.copyWith(
          isPolling: false,
          activeJobStatus: 'failed',
          errorMessage: status.error ?? status.message,
          jobMessage: status.message,
        );
      }
    } on ApiException catch (error) {
      _stopPolling();
      state = state.copyWith(
        isPolling: false,
        errorMessage: error.message,
        jobMessage: error.message,
      );
    }
  }

  Future<void> translateResults() async {
    if (state.liveResults.isEmpty) {
      return;
    }
    try {
      final payloads = state.liveResults
          .map(
            (ProductResult item) => item.normalizedProduct.isNotEmpty
                ? item.normalizedProduct
                : item.rawProduct,
          )
          .toList();
      final translated = await ref
          .read(crawlRepositoryProvider)
          .translate(payloads);
      final merged = <ProductResult>[];
      for (int index = 0; index < state.liveResults.length; index++) {
        final current = state.liveResults[index];
        final translatedProduct = index < translated.length
            ? translated[index]
            : current.normalizedProduct;
        merged.add(
          current.copyWith(
            name:
                (translatedProduct['translated_title'] ??
                        translatedProduct['title'] ??
                        current.name)
                    .toString(),
            translation: 100,
            normalizedProduct: translatedProduct,
          ),
        );
      }
      state = state.copyWith(
        liveResults: merged,
        jobMessage: 'Đã dịch dữ liệu sản phẩm',
      );
    } on ApiException catch (error) {
      state = state.copyWith(errorMessage: error.message);
    }
  }

  Future<void> mapResults() async {
    if (state.liveResults.isEmpty) {
      return;
    }
    try {
      final payloads = state.liveResults
          .map(
            (ProductResult item) => item.normalizedProduct.isNotEmpty
                ? item.normalizedProduct
                : item.rawProduct,
          )
          .toList();
      final mapped = await ref
          .read(crawlRepositoryProvider)
          .mapToOzon(payloads);
      final merged = <ProductResult>[];
      for (int index = 0; index < state.liveResults.length; index++) {
        final current = state.liveResults[index];
        final mappedProduct = index < mapped.length
            ? mapped[index]
            : current.mappedProduct;
        final rowData = mappedProduct['row_data'];
        final rowMap = rowData is Map<String, dynamic>
            ? rowData
            : rowData is Map
            ? rowData.map(
                (dynamic key, dynamic value) => MapEntry(key.toString(), value),
              )
            : <String, dynamic>{};
        merged.add(
          current.copyWith(
            sku: (rowMap['Article code*'] ?? current.sku).toString(),
            mapping: 100,
            mappedProduct: mappedProduct,
          ),
        );
      }
      state = state.copyWith(
        liveResults: merged,
        jobMessage: 'Đã mapping sang Ozon',
      );
    } on ApiException catch (error) {
      state = state.copyWith(errorMessage: error.message);
    }
  }

  Future<void> exportResults() async {
    if (state.liveResults.isEmpty) {
      return;
    }
    try {
      final payloads = state.liveResults
          .map(
            (ProductResult item) => item.mappedProduct.isNotEmpty
                ? item.mappedProduct
                : item.normalizedProduct.isNotEmpty
                ? item.normalizedProduct
                : item.rawProduct,
          )
          .toList();
      final exportResult = await ref
          .read(crawlRepositoryProvider)
          .export(payloads);
      state = state.copyWith(
        exportResult: exportResult,
        liveResults: state.liveResults
            .map((ProductResult item) => item.copyWith(exported: true))
            .toList(),
        jobMessage: 'Đã export Excel thành công',
      );
    } on ApiException catch (error) {
      state = state.copyWith(errorMessage: error.message);
    }
  }
}
