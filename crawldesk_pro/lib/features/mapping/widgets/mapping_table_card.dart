import 'package:flutter/material.dart';

import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_badge.dart';

class MappingTableCard extends StatelessWidget {
  const MappingTableCard({super.key});

  @override
  Widget build(BuildContext context) {
    final rows = <Map<String, String>>[
      <String, String>{
        'field': 'title',
        'source': 'product_title',
        'transform': 'Trim',
        'status': 'Đã map',
      },
      <String, String>{
        'field': 'description',
        'source': 'description_full',
        'transform': 'EN -> RU',
        'status': 'Đã map',
      },
      <String, String>{
        'field': 'price',
        'source': 'price',
        'transform': 'JPY -> RUB',
        'status': 'Đã map',
      },
      <String, String>{
        'field': 'color',
        'source': 'color',
        'transform': 'Chuẩn hóa',
        'status': 'Cần rà soát',
      },
      <String, String>{
        'field': 'weight_kg',
        'source': 'weight',
        'transform': 'g -> kg',
        'status': 'Thiếu dữ liệu',
      },
    ];

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Mapping trường Ozon',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: const <DataColumn>[
                DataColumn(label: Text('Trường Ozon')),
                DataColumn(label: Text('Nguồn dữ liệu')),
                DataColumn(label: Text('Biến đổi')),
                DataColumn(label: Text('Trạng thái')),
              ],
              rows: rows
                  .map(
                    (row) => DataRow(
                      cells: <DataCell>[
                        DataCell(Text(row['field']!)),
                        DataCell(
                          DropdownButton<String>(
                            value: row['source'],
                            underline: const SizedBox.shrink(),
                            items:
                                <String>[
                                      row['source']!,
                                      'category',
                                      'images',
                                      'stock',
                                    ]
                                    .map(
                                      (String value) =>
                                          DropdownMenuItem<String>(
                                            value: value,
                                            child: Text(value),
                                          ),
                                    )
                                    .toList(),
                            onChanged: (_) {},
                          ),
                        ),
                        DataCell(Text(row['transform']!)),
                        DataCell(
                          StatusBadge(
                            row['status']!,
                            color: row['status'] == 'Đã map'
                                ? Colors.green
                                : row['status'] == 'Cần rà soát'
                                ? Colors.orange
                                : Colors.red,
                          ),
                        ),
                      ],
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}
