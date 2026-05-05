class ExportResult {
  const ExportResult({
    required this.fileId,
    required this.fileName,
    required this.downloadUrl,
  });

  final String fileId;
  final String fileName;
  final String downloadUrl;

  factory ExportResult.fromJson(Map<String, dynamic> json) {
    return ExportResult(
      fileId: (json['file_id'] ?? '').toString(),
      fileName: (json['file_name'] ?? '').toString(),
      downloadUrl: (json['download_url'] ?? '').toString(),
    );
  }
}
