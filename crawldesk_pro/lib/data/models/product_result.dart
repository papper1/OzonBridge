class ProductResult {
  const ProductResult({
    required this.id,
    required this.source,
    required this.name,
    required this.sku,
    required this.price,
    required this.status,
    required this.mapping,
    required this.translation,
    required this.exported,
    required this.updatedAt,
    required this.productCount,
    this.productUrl = '',
    this.rawFilePath = '',
    this.normalizedFilePath = '',
    this.exportFilePath = '',
    this.rawProduct = const <String, dynamic>{},
    this.normalizedProduct = const <String, dynamic>{},
    this.mappedProduct = const <String, dynamic>{},
  });

  final String id;
  final String source;
  final String name;
  final String sku;
  final String price;
  final String status;
  final int mapping;
  final int translation;
  final bool exported;
  final String updatedAt;
  final int productCount;
  final String productUrl;
  final String rawFilePath;
  final String normalizedFilePath;
  final String exportFilePath;
  final Map<String, dynamic> rawProduct;
  final Map<String, dynamic> normalizedProduct;
  final Map<String, dynamic> mappedProduct;

  factory ProductResult.fromJson(Map<String, dynamic> json) {
    return ProductResult(
      id: (json['id'] ?? '').toString(),
      source: (json['source'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      sku: (json['sku'] ?? '').toString(),
      price: (json['price'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      mapping: _asInt(json['mapping']),
      translation: _asInt(json['translation']),
      exported: json['exported'] == true,
      updatedAt: (json['updated_at'] ?? json['updatedAt'] ?? '').toString(),
      productCount: _asInt(json['product_count'] ?? json['productCount']),
      productUrl: (json['product_url'] ?? '').toString(),
      rawFilePath: (json['raw_file_path'] ?? '').toString(),
      normalizedFilePath: (json['normalized_file_path'] ?? '').toString(),
      exportFilePath: (json['export_file_path'] ?? '').toString(),
      rawProduct: _asMap(json['raw_product']),
      normalizedProduct: _asMap(json['normalized_product']),
      mappedProduct: _asMap(json['mapped_product']),
    );
  }

  ProductResult copyWith({
    String? name,
    String? sku,
    String? price,
    String? status,
    int? mapping,
    int? translation,
    bool? exported,
    String? rawFilePath,
    String? normalizedFilePath,
    String? exportFilePath,
    Map<String, dynamic>? rawProduct,
    Map<String, dynamic>? normalizedProduct,
    Map<String, dynamic>? mappedProduct,
  }) {
    return ProductResult(
      id: id,
      source: source,
      name: name ?? this.name,
      sku: sku ?? this.sku,
      price: price ?? this.price,
      status: status ?? this.status,
      mapping: mapping ?? this.mapping,
      translation: translation ?? this.translation,
      exported: exported ?? this.exported,
      updatedAt: updatedAt,
      productCount: productCount,
      productUrl: productUrl,
      rawFilePath: rawFilePath ?? this.rawFilePath,
      normalizedFilePath: normalizedFilePath ?? this.normalizedFilePath,
      exportFilePath: exportFilePath ?? this.exportFilePath,
      rawProduct: rawProduct ?? this.rawProduct,
      normalizedProduct: normalizedProduct ?? this.normalizedProduct,
      mappedProduct: mappedProduct ?? this.mappedProduct,
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

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (dynamic key, dynamic value) => MapEntry(key.toString(), value),
    );
  }
  return const <String, dynamic>{};
}
