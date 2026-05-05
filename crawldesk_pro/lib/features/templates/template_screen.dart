import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/widgets/app_card.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_badge.dart';
import '../../data/models/ozon_template.dart';
import '../../data/repositories/local_template_repository.dart';
import 'widgets/template_detail_card.dart';

class TemplateScreen extends ConsumerStatefulWidget {
  const TemplateScreen({super.key});

  @override
  ConsumerState<TemplateScreen> createState() => _TemplateScreenState();
}

class _TemplateScreenState extends ConsumerState<TemplateScreen> {
  String _searchQuery = '';
  String? _selectedKey;

  @override
  Widget build(BuildContext context) {
    final templatesAsync = ref.watch(localTemplatesProvider);
    final templates = templatesAsync.valueOrNull ?? const <OzonTemplate>[];
    final filtered = templates.where((OzonTemplate template) {
      final haystack = '${template.name} ${template.category} ${template.fileName}'
          .toLowerCase();
      return _searchQuery.isEmpty || haystack.contains(_searchQuery);
    }).toList();
    final selected = _resolveSelected(filtered);
    final repository = ref.read(localTemplateRepositoryProvider);

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Template', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          const Text(
            'Quản lý template Ozon local: import file .xlsx, lưu JSON config và CRUD trực tiếp.',
          ),
          const SizedBox(height: AppSizes.sectionGap),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              PrimaryButton(
                label: 'Tải template lên',
                icon: Icons.upload_file_rounded,
                onPressed: () => _openTemplateDialog(context, ref),
              ),
              PrimaryButton(
                label: 'Tạo template mới',
                icon: Icons.add_rounded,
                onPressed: () => _openTemplateDialog(
                  context,
                  ref,
                  requireWorkbook: false,
                ),
              ),
              PrimaryButton(
                label: 'Mở thư mục template',
                icon: Icons.folder_open_rounded,
                variant: ButtonVariant.secondary,
                onPressed: () => _openFolder(repository.templatesDirPath),
              ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            onChanged: (String value) {
              setState(() => _searchQuery = value.trim().toLowerCase());
            },
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search_rounded),
              hintText: 'Tìm template...',
            ),
          ),
          const SizedBox(height: AppSizes.sectionGap),
          if (templatesAsync.hasError)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                'Không đọc được template local.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.error,
                ),
              ),
            ),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Danh sách template',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                if (filtered.isEmpty)
                  const Text('Chưa có template local phù hợp.')
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const <DataColumn>[
                        DataColumn(label: Text('Tên template')),
                        DataColumn(label: Text('Danh mục')),
                        DataColumn(label: Text('Phiên bản')),
                        DataColumn(label: Text('Số trường')),
                        DataColumn(label: Text('Trạng thái')),
                        DataColumn(label: Text('Hành động')),
                      ],
                      rows: filtered
                          .map(
                            (template) => DataRow(
                              selected: selected?.key == template.key,
                              onSelectChanged: (_) {
                                setState(() => _selectedKey = template.key);
                              },
                              cells: <DataCell>[
                                DataCell(Text(template.name)),
                                DataCell(Text(template.category)),
                                DataCell(Text(template.version)),
                                DataCell(Text('${template.fieldCount}')),
                                DataCell(
                                  StatusBadge(
                                    template.status,
                                    color: template.status == 'Đồng bộ'
                                        ? AppColors.success
                                        : AppColors.warning,
                                  ),
                                ),
                                DataCell(
                                  PopupMenuButton<String>(
                                    onSelected: (String action) {
                                      _handleAction(
                                        context,
                                        ref,
                                        template,
                                        action,
                                      );
                                    },
                                    itemBuilder: (BuildContext context) =>
                                        <PopupMenuEntry<String>>[
                                          const PopupMenuItem<String>(
                                            value: 'edit',
                                            child: Text('Sửa'),
                                          ),
                                          const PopupMenuItem<String>(
                                            value: 'excel',
                                            child: Text('Mở Excel'),
                                          ),
                                          const PopupMenuItem<String>(
                                            value: 'json',
                                            child: Text('Mở JSON'),
                                          ),
                                          const PopupMenuItem<String>(
                                            value: 'folder',
                                            child: Text('Mở thư mục'),
                                          ),
                                          const PopupMenuItem<String>(
                                            value: 'delete',
                                            child: Text('Xóa'),
                                          ),
                                        ],
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
          ),
          const SizedBox(height: AppSizes.sectionGap),
          TemplateDetailCard(template: selected),
        ],
      ),
    );
  }

  OzonTemplate? _resolveSelected(List<OzonTemplate> templates) {
    if (templates.isEmpty) {
      return null;
    }
    if (_selectedKey == null) {
      return templates.first;
    }
    for (final template in templates) {
      if (template.key == _selectedKey) {
        return template;
      }
    }
    return templates.first;
  }

  Future<void> _handleAction(
    BuildContext context,
    WidgetRef ref,
    OzonTemplate template,
    String action,
  ) async {
    switch (action) {
      case 'edit':
        await _openTemplateDialog(context, ref, template: template);
        return;
      case 'excel':
        await _openPath(template.workbookAbsolutePath);
        return;
      case 'json':
        await _openPath(template.jsonFilePath);
        return;
      case 'folder':
        await _openFolder(File(template.jsonFilePath).parent.path);
        return;
      case 'delete':
        await _confirmDelete(context, ref, template);
        return;
    }
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    OzonTemplate template,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Xóa template'),
          content: Text('Xóa template "${template.name}" khỏi local?'),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Xóa'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    try {
      await ref.read(localTemplateRepositoryProvider).deleteTemplate(template);
      ref.invalidate(localTemplatesProvider);
      setState(() => _selectedKey = null);
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      _showSnack(context, 'Không thể xóa template: $error');
    }
  }

  Future<void> _openTemplateDialog(
    BuildContext context,
    WidgetRef ref, {
    OzonTemplate? template,
    bool requireWorkbook = true,
  }) async {
    final templates = await ref.read(localTemplatesProvider.future);
    if (!context.mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (BuildContext context) {
        return _TemplateEditorDialog(
          template: template,
          templates: templates,
          requireWorkbook: requireWorkbook,
          onSaved: () {
            ref.invalidate(localTemplatesProvider);
            setState(() => _selectedKey = template?.key);
          },
        );
      },
    );
  }

  void _showSnack(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

class _TemplateEditorDialog extends ConsumerStatefulWidget {
  const _TemplateEditorDialog({
    required this.templates,
    required this.onSaved,
    this.template,
    this.requireWorkbook = true,
  });

  final OzonTemplate? template;
  final List<OzonTemplate> templates;
  final VoidCallback onSaved;
  final bool requireWorkbook;

  @override
  ConsumerState<_TemplateEditorDialog> createState() =>
      _TemplateEditorDialogState();
}

class _TemplateEditorDialogState extends ConsumerState<_TemplateEditorDialog> {
  late final TextEditingController _nameController;
  late final TextEditingController _categoryController;
  late final TextEditingController _versionController;
  late final TextEditingController _workbookController;
  late final TextEditingController _requiredFieldsController;
  late final TextEditingController _sheetNameController;
  late final TextEditingController _headerRowController;
  late final TextEditingController _dataStartRowController;

  late String _status;
  late String _baseTemplateKey;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    final template = widget.template;
    _nameController = TextEditingController(text: template?.name ?? '');
    _categoryController = TextEditingController(
      text: template?.category ?? '',
    );
    _versionController = TextEditingController(text: template?.version ?? 'v1.0');
    _workbookController = TextEditingController(
      text: template?.workbookAbsolutePath ?? '',
    );
    _requiredFieldsController = TextEditingController(
      text: template?.requiredFields.join(', ') ?? '',
    );
    _sheetNameController = TextEditingController(
      text: template?.sheetName ?? 'Template',
    );
    _headerRowController = TextEditingController(
      text: '${template?.headerRow ?? 2}',
    );
    _dataStartRowController = TextEditingController(
      text: '${template?.dataStartRow ?? 5}',
    );
    _status = template?.status ?? 'Đồng bộ';
    _baseTemplateKey =
        template?.key ?? (widget.templates.isNotEmpty ? widget.templates.first.key : 'generic');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _categoryController.dispose();
    _versionController.dispose();
    _workbookController.dispose();
    _requiredFieldsController.dispose();
    _sheetNameController.dispose();
    _headerRowController.dispose();
    _dataStartRowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.template == null ? 'Thêm template' : 'Sửa template'),
      content: SizedBox(
        width: 620,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Tên template'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _categoryController,
                decoration: const InputDecoration(labelText: 'Danh mục'),
              ),
              const SizedBox(height: 12),
              Row(
                children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: _versionController,
                      decoration: const InputDecoration(labelText: 'Phiên bản'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: _status,
                      decoration: const InputDecoration(labelText: 'Trạng thái'),
                      items: const <String>['Đồng bộ', 'Cần rà soát']
                          .map(
                            (String item) => DropdownMenuItem<String>(
                              value: item,
                              child: Text(item),
                            ),
                          )
                          .toList(),
                      onChanged: (String? value) {
                        if (value != null) {
                          setState(() => _status = value);
                        }
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _baseTemplateKey,
                decoration: const InputDecoration(labelText: 'Base config để copy'),
                items: widget.templates
                    .map(
                      (OzonTemplate item) => DropdownMenuItem<String>(
                        value: item.key,
                        child: Text(item.name),
                      ),
                    )
                    .toList(),
                onChanged: widget.template == null
                    ? (String? value) {
                        if (value != null) {
                          setState(() => _baseTemplateKey = value);
                        }
                      }
                    : null,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _workbookController,
                decoration: InputDecoration(
                  labelText: widget.requireWorkbook
                      ? 'Đường dẫn file .xlsx từ máy'
                      : 'Đường dẫn file .xlsx từ máy (tùy chọn)',
                  hintText:
                      r'Ví dụ: C:\Users\thang\Downloads\ozon_template.xlsx',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _requiredFieldsController,
                minLines: 2,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Required fields, ngăn cách bởi dấu phẩy',
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: _sheetNameController,
                      decoration: const InputDecoration(labelText: 'Sheet name'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _headerRowController,
                      decoration: const InputDecoration(labelText: 'Header row'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _dataStartRowController,
                      decoration: const InputDecoration(labelText: 'Data start row'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: _isSaving ? null : () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: _isSaving ? null : _save,
          child: Text(_isSaving ? 'Đang lưu...' : 'Lưu'),
        ),
      ],
    );
  }

  Future<void> _save() async {
    final name = _nameController.text.trim();
    final category = _categoryController.text.trim();
    final version = _versionController.text.trim();
    final workbookPath = _workbookController.text.trim();
    final requiredFields = _requiredFieldsController.text
        .split(',')
        .map((String item) => item.trim())
        .where((String item) => item.isNotEmpty)
        .toList();
    final sheetName = _sheetNameController.text.trim();
    final headerRow = int.tryParse(_headerRowController.text.trim()) ?? 2;
    final dataStartRow = int.tryParse(_dataStartRowController.text.trim()) ?? 5;

    if (name.isEmpty || category.isEmpty || version.isEmpty) {
      _showError('Tên, danh mục và phiên bản là bắt buộc.');
      return;
    }
    if (widget.requireWorkbook && workbookPath.isEmpty && widget.template == null) {
      _showError('Bạn cần nhập đường dẫn file .xlsx.');
      return;
    }

    setState(() => _isSaving = true);
    try {
      final repository = ref.read(localTemplateRepositoryProvider);
      if (widget.template == null) {
        await repository.createTemplate(
          name: name,
          category: category,
          version: version,
          status: _status,
          sourceWorkbookPath: workbookPath,
          baseTemplateKey: _baseTemplateKey,
          requiredFields: requiredFields,
          sheetName: sheetName.isEmpty ? 'Template' : sheetName,
          headerRow: headerRow,
          dataStartRow: dataStartRow,
        );
      } else {
        await repository.updateTemplate(
          template: widget.template!,
          name: name,
          category: category,
          version: version,
          status: _status,
          sourceWorkbookPath: workbookPath,
          requiredFields: requiredFields,
          sheetName: sheetName.isEmpty ? 'Template' : sheetName,
          headerRow: headerRow,
          dataStartRow: dataStartRow,
        );
      }
      widget.onSaved();
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (error) {
      _showError(error.toString());
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

Future<void> _openPath(String path) async {
  if (path.isEmpty) {
    return;
  }
  final file = File(path);
  if (!file.existsSync()) {
    return;
  }
  if (Platform.isWindows) {
    await Process.start('cmd', <String>['/c', 'start', '', path]);
    return;
  }
  await Process.start(path, const <String>[]);
}

Future<void> _openFolder(String path) async {
  if (path.isEmpty) {
    return;
  }
  final directory = Directory(path);
  if (!directory.existsSync()) {
    return;
  }
  if (Platform.isWindows) {
    await Process.start('explorer.exe', <String>[path]);
    return;
  }
  await Process.start(path, const <String>[]);
}
