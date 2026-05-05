class OzonTemplate {
  const OzonTemplate({
    required this.key,
    required this.name,
    required this.category,
    required this.version,
    required this.fieldCount,
    required this.requiredFieldCount,
    required this.status,
    required this.fileName,
    required this.requiredFields,
    required this.jsonFilePath,
    required this.workbookTemplate,
    required this.workbookAbsolutePath,
    required this.fieldMapKeys,
    required this.sheetName,
    required this.headerRow,
    required this.dataStartRow,
  });

  final String key;
  final String name;
  final String category;
  final String version;
  final int fieldCount;
  final int requiredFieldCount;
  final String status;
  final String fileName;
  final List<String> requiredFields;
  final String jsonFilePath;
  final String workbookTemplate;
  final String workbookAbsolutePath;
  final List<String> fieldMapKeys;
  final String sheetName;
  final int headerRow;
  final int dataStartRow;

  OzonTemplate copyWith({
    String? key,
    String? name,
    String? category,
    String? version,
    int? fieldCount,
    int? requiredFieldCount,
    String? status,
    String? fileName,
    List<String>? requiredFields,
    String? jsonFilePath,
    String? workbookTemplate,
    String? workbookAbsolutePath,
    List<String>? fieldMapKeys,
    String? sheetName,
    int? headerRow,
    int? dataStartRow,
  }) {
    return OzonTemplate(
      key: key ?? this.key,
      name: name ?? this.name,
      category: category ?? this.category,
      version: version ?? this.version,
      fieldCount: fieldCount ?? this.fieldCount,
      requiredFieldCount: requiredFieldCount ?? this.requiredFieldCount,
      status: status ?? this.status,
      fileName: fileName ?? this.fileName,
      requiredFields: requiredFields ?? this.requiredFields,
      jsonFilePath: jsonFilePath ?? this.jsonFilePath,
      workbookTemplate: workbookTemplate ?? this.workbookTemplate,
      workbookAbsolutePath: workbookAbsolutePath ?? this.workbookAbsolutePath,
      fieldMapKeys: fieldMapKeys ?? this.fieldMapKeys,
      sheetName: sheetName ?? this.sheetName,
      headerRow: headerRow ?? this.headerRow,
      dataStartRow: dataStartRow ?? this.dataStartRow,
    );
  }
}
