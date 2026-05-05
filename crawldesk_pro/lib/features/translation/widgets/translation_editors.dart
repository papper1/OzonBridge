import 'package:flutter/material.dart';

import '../../../core/widgets/app_card.dart';

class TranslationEditors extends StatelessWidget {
  const TranslationEditors({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: _EditorCard(
            title: 'Nội dung gốc',
            content:
                'Áo hoodie nam nữ unisex oversize phong cách Hàn Quốc. Chất nỉ mềm, form rộng, phù hợp mặc hàng ngày.',
          ),
        ),
        const SizedBox(width: 16),
        const Expanded(
          child: _EditorCard(
            title: 'Bản dịch tiếng Nga',
            content:
                'Худи унисекс оверсайз в корейском стиле. Мягкий материал, свободный силуэт, подходит для повседневной носки.',
          ),
        ),
      ],
    );
  }
}

class _EditorCard extends StatelessWidget {
  const _EditorCard({required this.title, required this.content});

  final String title;
  final String content;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          TextField(
            controller: TextEditingController(text: content),
            maxLines: 9,
            decoration: const InputDecoration(border: OutlineInputBorder()),
          ),
        ],
      ),
    );
  }
}
