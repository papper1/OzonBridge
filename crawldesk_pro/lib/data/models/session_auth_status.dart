class SessionAuthStatus {
  const SessionAuthStatus({
    required this.exists,
    required this.valid,
    required this.flowActive,
    required this.sessionPath,
    required this.message,
  });

  final bool exists;
  final bool valid;
  final bool flowActive;
  final String sessionPath;
  final String message;

  factory SessionAuthStatus.fromJson(Map<String, dynamic> json) {
    return SessionAuthStatus(
      exists: json['exists'] == true,
      valid: json['valid'] == true,
      flowActive: json['flow_active'] == true,
      sessionPath: (json['session_path'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
    );
  }
}
