class CrawlStatus {
  const CrawlStatus({
    required this.jobId,
    required this.status,
    this.message = '',
    this.error,
    this.processed = 0,
    this.total = 0,
    this.stage = '',
    this.updatedAt = '',
  });

  final String jobId;
  final String status;
  final String message;
  final String? error;
  final int processed;
  final int total;
  final String stage;
  final String updatedAt;

  factory CrawlStatus.fromJson(Map<String, dynamic> json) {
    final progress = json['progress'];
    final progressMap = progress is Map<String, dynamic>
        ? progress
        : <String, dynamic>{};
    return CrawlStatus(
      jobId: (json['job_id'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      error: json['error']?.toString(),
      processed: _asInt(progressMap['processed']),
      total: _asInt(progressMap['total']),
      stage: (progressMap['stage'] ?? '').toString(),
      updatedAt: (json['updated_at'] ?? '').toString(),
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
