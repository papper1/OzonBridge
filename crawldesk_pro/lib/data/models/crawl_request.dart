class CrawlRequest {
  const CrawlRequest({
    required this.platform,
    this.keyword,
    this.productUrl,
    this.shopUrl,
    this.inputMode,
    this.maxLinks = 5,
    this.translateToRussian = true,
    this.mapToOzon = true,
    this.exportExcel = true,
    this.templateName,
  });

  final String platform;
  final String? keyword;
  final String? productUrl;
  final String? shopUrl;
  final String? inputMode;
  final int maxLinks;
  final bool translateToRussian;
  final bool mapToOzon;
  final bool exportExcel;
  final String? templateName;

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'platform': platform,
      if (keyword != null && keyword!.isNotEmpty) 'keyword': keyword,
      if (productUrl != null && productUrl!.isNotEmpty)
        'product_url': productUrl,
      if (shopUrl != null && shopUrl!.isNotEmpty) 'shop_url': shopUrl,
      'options': <String, dynamic>{
        if (inputMode != null) 'input_mode': inputMode,
        'max_links': maxLinks,
        'translate_to_russian': translateToRussian,
        'map_to_ozon': mapToOzon,
        'export_excel': exportExcel,
        if (templateName != null && templateName!.isNotEmpty)
          'template_name': templateName,
      },
    };
  }
}
