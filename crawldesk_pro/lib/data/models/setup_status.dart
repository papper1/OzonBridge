class SetupStatus {
  const SetupStatus({
    required this.envFileExists,
    required this.zyteApiKeyConfigured,
    required this.openAiApiKeyConfigured,
    required this.openAiModel,
    required this.sessionFileExists,
    required this.sessionValid,
    required this.sessionFlowActive,
    required this.envFilePath,
    required this.sessionFilePath,
    required this.sessionMessage,
  });

  final bool envFileExists;
  final bool zyteApiKeyConfigured;
  final bool openAiApiKeyConfigured;
  final String openAiModel;
  final bool sessionFileExists;
  final bool sessionValid;
  final bool sessionFlowActive;
  final String envFilePath;
  final String sessionFilePath;
  final String sessionMessage;

  bool get isReadyFor1688 => sessionValid;
  bool get isReadyForZyteSources => zyteApiKeyConfigured;
  bool get isReadyForTranslation => openAiApiKeyConfigured;

  SetupStatus copyWith({
    bool? envFileExists,
    bool? zyteApiKeyConfigured,
    bool? openAiApiKeyConfigured,
    String? openAiModel,
    bool? sessionFileExists,
    bool? sessionValid,
    bool? sessionFlowActive,
    String? envFilePath,
    String? sessionFilePath,
    String? sessionMessage,
  }) {
    return SetupStatus(
      envFileExists: envFileExists ?? this.envFileExists,
      zyteApiKeyConfigured:
          zyteApiKeyConfigured ?? this.zyteApiKeyConfigured,
      openAiApiKeyConfigured:
          openAiApiKeyConfigured ?? this.openAiApiKeyConfigured,
      openAiModel: openAiModel ?? this.openAiModel,
      sessionFileExists: sessionFileExists ?? this.sessionFileExists,
      sessionValid: sessionValid ?? this.sessionValid,
      sessionFlowActive: sessionFlowActive ?? this.sessionFlowActive,
      envFilePath: envFilePath ?? this.envFilePath,
      sessionFilePath: sessionFilePath ?? this.sessionFilePath,
      sessionMessage: sessionMessage ?? this.sessionMessage,
    );
  }
}
