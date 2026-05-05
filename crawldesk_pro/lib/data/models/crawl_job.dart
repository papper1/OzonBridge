class CrawlJob {
  const CrawlJob({
    required this.id,
    required this.status,
    this.message = '',
    this.source = '',
    this.mode = '',
    this.total = 0,
    this.processed = 0,
    this.success = 0,
    this.failed = 0,
    this.updatedAt = '',
  });

  final String id;
  final String message;
  final String source;
  final String mode;
  final String status;
  final int total;
  final int processed;
  final int success;
  final int failed;
  final String updatedAt;

  factory CrawlJob.fromJson(Map<String, dynamic> json) {
    return CrawlJob(
      id: (json['job_id'] ?? json['id'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      source: (json['source'] ?? '').toString(),
      mode: (json['mode'] ?? '').toString(),
      total: _asInt(json['total']),
      processed: _asInt(json['processed']),
      success: _asInt(json['success']),
      failed: _asInt(json['failed']),
      updatedAt: (json['updated_at'] ?? json['updatedAt'] ?? '').toString(),
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
