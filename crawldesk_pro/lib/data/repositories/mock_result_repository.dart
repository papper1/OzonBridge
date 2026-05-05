import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/product_result.dart';

final mockResultRepositoryProvider = Provider<MockResultRepository>(
  (ref) => const MockResultRepository(),
);

class MockResultRepository {
  const MockResultRepository();

  List<ProductResult> allResults() => const <ProductResult>[
    ProductResult(
      id: 'RES-20260501-002',
      source: '1688',
      name: 'Áo hoodie nam nữ unisex oversize',
      sku: 'HD001-IVORY-L',
      price: '¥89.00',
      status: 'Hoàn tất',
      mapping: 100,
      translation: 100,
      exported: true,
      updatedAt: '01/05/2026 08:20',
      productCount: 4000,
    ),
    ProductResult(
      id: 'RES-20260430-009',
      source: 'SHEIN',
      name: 'Women’s Floral Print Midi Dress',
      sku: 'DRS024-FLORAL-M',
      price: '\$24.90',
      status: 'Đang chạy',
      mapping: 63,
      translation: 76,
      exported: false,
      updatedAt: '30/04/2026 21:02',
      productCount: 2132,
    ),
    ProductResult(
      id: 'RES-20260430-006',
      source: 'Etsy',
      name: 'Handmade Ceramic Mug Set',
      sku: 'MUGSET-HM-02',
      price: '\$18.50',
      status: 'Cần rà soát',
      mapping: 85,
      translation: 91,
      exported: false,
      updatedAt: '30/04/2026 19:48',
      productCount: 850,
    ),
    ProductResult(
      id: 'RES-20260429-004',
      source: 'eBay',
      name: 'Nike Air Max 270 Men’s Shoes',
      sku: 'AM270-BLK-42',
      price: '\$129.99',
      status: 'Hoàn tất',
      mapping: 100,
      translation: 100,
      exported: true,
      updatedAt: '29/04/2026 16:30',
      productCount: 2500,
    ),
  ];
}
