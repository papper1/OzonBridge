import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/crawl_job.dart';
import '../models/ozon_template.dart';

final mockCrawlRepositoryProvider = Provider<MockCrawlRepository>(
  (ref) => const MockCrawlRepository(),
);

class MockCrawlRepository {
  const MockCrawlRepository();

  List<String> get sources => const <String>['1688', 'SHEIN', 'Etsy', 'eBay'];

  List<OzonTemplate> get templates => const <OzonTemplate>[
    OzonTemplate(
      key: 'ozon_template_v3_1',
      name: 'OZON_Template_v3.1',
      category: 'Thời trang > Hoodie',
      version: 'v3.1',
      fieldCount: 168,
      requiredFieldCount: 12,
      status: 'Đồng bộ',
      fileName: 'OZON_Template_v3.1.xlsx',
      requiredFields: <String>[
        'title',
        'description',
        'price',
        'images',
        'sku',
        'brand',
      ],
      jsonFilePath: '',
      workbookTemplate: '',
      workbookAbsolutePath: '',
      fieldMapKeys: <String>[],
      sheetName: 'Template',
      headerRow: 2,
      dataStartRow: 5,
    ),
    OzonTemplate(
      key: 'ozon_fashion_v1_5',
      name: 'OZON_Fashion_v1.5',
      category: 'Thời trang > Dress',
      version: 'v1.5',
      fieldCount: 132,
      requiredFieldCount: 10,
      status: 'Cần rà soát',
      fileName: 'OZON_Fashion_v1.5.xlsx',
      requiredFields: <String>['title', 'color', 'size', 'material'],
      jsonFilePath: '',
      workbookTemplate: '',
      workbookAbsolutePath: '',
      fieldMapKeys: <String>[],
      sheetName: 'Template',
      headerRow: 2,
      dataStartRow: 5,
    ),
    OzonTemplate(
      key: 'ozon_home_v2_0',
      name: 'OZON_Home_v2.0',
      category: 'Home & Living',
      version: 'v2.0',
      fieldCount: 142,
      requiredFieldCount: 11,
      status: 'Đồng bộ',
      fileName: 'OZON_Home_v2.0.xlsx',
      requiredFields: <String>['title', 'weight', 'dimensions', 'images'],
      jsonFilePath: '',
      workbookTemplate: '',
      workbookAbsolutePath: '',
      fieldMapKeys: <String>[],
      sheetName: 'Template',
      headerRow: 2,
      dataStartRow: 5,
    ),
  ];

  List<CrawlJob> recentJobs() => const <CrawlJob>[
    CrawlJob(
      id: 'CRW-20260501-001',
      source: '1688',
      mode: 'URL sản phẩm',
      status: 'Đang chạy',
      total: 4000,
      processed: 2734,
      success: 2132,
      failed: 134,
      updatedAt: '01/05/2026 08:32',
    ),
    CrawlJob(
      id: 'CRW-20260430-014',
      source: 'SHEIN',
      mode: 'Từ khóa',
      status: 'Hoàn tất',
      total: 1200,
      processed: 1200,
      success: 1158,
      failed: 42,
      updatedAt: '30/04/2026 21:12',
    ),
    CrawlJob(
      id: 'CRW-20260430-011',
      source: 'Etsy',
      mode: 'Theo shop',
      status: 'Hoàn tất',
      total: 850,
      processed: 850,
      success: 812,
      failed: 38,
      updatedAt: '30/04/2026 18:45',
    ),
    CrawlJob(
      id: 'CRW-20260429-006',
      source: 'eBay',
      mode: 'URL sản phẩm',
      status: 'Lỗi',
      total: 2500,
      processed: 2500,
      success: 2402,
      failed: 98,
      updatedAt: '29/04/2026 17:20',
    ),
  ];
}
