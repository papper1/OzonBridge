import '../../data/models/export_result.dart';
import '../../data/models/product_result.dart';

class CrawlState {
  const CrawlState({
    this.tab = 'URL sản phẩm',
    this.source = '1688',
    this.mode = 'Nhanh',
    this.template = 'OZON_Template_v3.1.xlsx',
    this.concurrentThreads = 10,
    this.useProxy = true,
    this.translateToRussian = true,
    this.exportExcel = true,
    this.input = 'https://detail.1688.com/offer/1234567890.html',
    this.didCheckBackend = false,
    this.isCheckingBackend = false,
    this.backendAvailable = false,
    this.backendMessage = 'Chưa kiểm tra backend',
    this.isSubmitting = false,
    this.isPolling = false,
    this.activeJobId,
    this.activeJobStatus = 'idle',
    this.jobMessage = '',
    this.errorMessage,
    this.liveResults = const <ProductResult>[],
    this.exportResult,
    this.processed = 0,
    this.total = 0,
    this.stage = '',
  });

  final String tab;
  final String source;
  final String mode;
  final String template;
  final double concurrentThreads;
  final bool useProxy;
  final bool translateToRussian;
  final bool exportExcel;
  final String input;
  final bool didCheckBackend;
  final bool isCheckingBackend;
  final bool backendAvailable;
  final String backendMessage;
  final bool isSubmitting;
  final bool isPolling;
  final String? activeJobId;
  final String activeJobStatus;
  final String jobMessage;
  final String? errorMessage;
  final List<ProductResult> liveResults;
  final ExportResult? exportResult;
  final int processed;
  final int total;
  final String stage;

  int get inputCount =>
      input.split('\n').where((String line) => line.trim().isNotEmpty).length;

  bool get canStart =>
      !isSubmitting &&
      !isPolling &&
      input.trim().isNotEmpty &&
      backendAvailable;

  CrawlState copyWith({
    String? tab,
    String? source,
    String? mode,
    String? template,
    double? concurrentThreads,
    bool? useProxy,
    bool? translateToRussian,
    bool? exportExcel,
    String? input,
    bool? didCheckBackend,
    bool? isCheckingBackend,
    bool? backendAvailable,
    String? backendMessage,
    bool? isSubmitting,
    bool? isPolling,
    String? activeJobId,
    bool clearActiveJobId = false,
    String? activeJobStatus,
    String? jobMessage,
    String? errorMessage,
    bool clearErrorMessage = false,
    List<ProductResult>? liveResults,
    ExportResult? exportResult,
    bool clearExportResult = false,
    int? processed,
    int? total,
    String? stage,
  }) {
    return CrawlState(
      tab: tab ?? this.tab,
      source: source ?? this.source,
      mode: mode ?? this.mode,
      template: template ?? this.template,
      concurrentThreads: concurrentThreads ?? this.concurrentThreads,
      useProxy: useProxy ?? this.useProxy,
      translateToRussian: translateToRussian ?? this.translateToRussian,
      exportExcel: exportExcel ?? this.exportExcel,
      input: input ?? this.input,
      didCheckBackend: didCheckBackend ?? this.didCheckBackend,
      isCheckingBackend: isCheckingBackend ?? this.isCheckingBackend,
      backendAvailable: backendAvailable ?? this.backendAvailable,
      backendMessage: backendMessage ?? this.backendMessage,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      isPolling: isPolling ?? this.isPolling,
      activeJobId: clearActiveJobId ? null : activeJobId ?? this.activeJobId,
      activeJobStatus: activeJobStatus ?? this.activeJobStatus,
      jobMessage: jobMessage ?? this.jobMessage,
      errorMessage: clearErrorMessage
          ? null
          : errorMessage ?? this.errorMessage,
      liveResults: liveResults ?? this.liveResults,
      exportResult: clearExportResult
          ? null
          : exportResult ?? this.exportResult,
      processed: processed ?? this.processed,
      total: total ?? this.total,
      stage: stage ?? this.stage,
    );
  }
}
