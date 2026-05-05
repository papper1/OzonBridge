class DashboardSummary {
  const DashboardSummary({
    required this.supportedSources,
    required this.totalCrawledProducts,
    required this.successRate,
    required this.exportedFiles,
    this.successfulProducts = 0,
    this.failedProducts = 0,
  });

  const DashboardSummary.empty()
    : supportedSources = const <String>[],
      totalCrawledProducts = 0,
      successRate = 0,
      exportedFiles = 0,
      successfulProducts = 0,
      failedProducts = 0;

  final List<String> supportedSources;
  final int totalCrawledProducts;
  final double successRate;
  final int exportedFiles;
  final int successfulProducts;
  final int failedProducts;

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    final sources = json['supported_sources'];
    return DashboardSummary(
      supportedSources: sources is List
          ? sources.map((dynamic item) => item.toString()).toList()
          : const <String>[],
      totalCrawledProducts: _asInt(json['total_crawled_products']),
      successRate: _asDouble(json['success_rate']),
      exportedFiles: _asInt(json['exported_files']),
      successfulProducts: _asInt(json['successful_products']),
      failedProducts: _asInt(json['failed_products']),
    );
  }
}

int _asInt(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is double) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _asDouble(dynamic value) {
  if (value is double) {
    return value;
  }
  if (value is int) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? 0;
}
