import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/app_sizes.dart';
import '../../core/widgets/primary_button.dart';
import '../../core/widgets/status_badge.dart';
import '../../data/models/setup_status.dart';
import '../../data/repositories/crawl_repository.dart';
import '../../data/repositories/local_setup_repository.dart';
import 'widgets/settings_section.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final TextEditingController _zyteController = TextEditingController();
  final TextEditingController _openAiController = TextEditingController();
  final TextEditingController _modelController = TextEditingController();

  bool _didLoadControllers = false;
  bool _isSaving = false;
  bool _isOpeningSession = false;
  bool _isSavingSession = false;
  String? _message;
  bool _isError = false;

  @override
  void dispose() {
    _zyteController.dispose();
    _openAiController.dispose();
    _modelController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final setupAsync = ref.watch(localSetupStatusProvider);
    final repository = ref.read(localSetupRepositoryProvider);
    final setupStatus = setupAsync.valueOrNull;

    if (setupStatus != null && !_didLoadControllers) {
      _didLoadControllers = true;
      _loadControllersFromStatus(setupStatus);
    }

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Cài đặt', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          const Text(
            'Thiết lập key runtime, kiểm tra session 1688 và chuẩn bị môi trường để app chạy thật.',
          ),
          const SizedBox(height: AppSizes.sectionGap),
          if (_message != null) ...<Widget>[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: (_isError ? AppColors.error : AppColors.success)
                    .withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                _message!,
                style: TextStyle(
                  color: _isError ? AppColors.error : AppColors.success,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: <Widget>[
              SizedBox(
                width: 420,
                child: SettingsSection(
                  title: 'Runtime setup',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      _SetupRow(
                        title: 'Zyte API key',
                        subtitle: 'Cần cho SHEIN, Etsy, eBay và các nguồn đi qua Zyte.',
                        badge: _buildStatusBadge(
                          ready: setupStatus?.isReadyForZyteSources == true,
                          readyText: 'Sẵn sàng',
                          missingText: 'Thiếu key',
                        ),
                      ),
                      const SizedBox(height: 10),
                      _SetupRow(
                        title: 'OpenAI API key',
                        subtitle: 'Cần khi bật Dịch tiếng Nga.',
                        badge: _buildStatusBadge(
                          ready: setupStatus?.isReadyForTranslation == true,
                          readyText: 'Sẵn sàng',
                          missingText: 'Thiếu key',
                        ),
                      ),
                      const SizedBox(height: 10),
                      _SetupRow(
                        title: 'Session 1688',
                        subtitle: setupStatus?.sessionMessage.isNotEmpty == true
                            ? setupStatus!.sessionMessage
                            : 'Cần cho crawl 1688 qua browser đã đăng nhập.',
                        badge: _buildStatusBadge(
                          ready: setupStatus?.isReadyFor1688 == true,
                          readyText: 'Hợp lệ',
                          missingText: setupStatus?.sessionFlowActive == true
                              ? 'Đang chờ lưu'
                              : 'Chưa sẵn sàng',
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'File cấu hình: ${setupStatus?.envFilePath ?? '-'}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Session 1688: ${setupStatus?.sessionFilePath ?? '-'}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(
                width: 520,
                child: SettingsSection(
                  title: 'API keys',
                  child: Column(
                    children: <Widget>[
                      TextField(
                        controller: _zyteController,
                        decoration: const InputDecoration(
                          labelText: 'ZYTE_API_KEY',
                          hintText: 'Zyte API key',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _openAiController,
                        decoration: const InputDecoration(
                          labelText: 'OPENAI_API_KEY',
                          hintText: 'sk-...',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _modelController,
                        decoration: const InputDecoration(
                          labelText: 'OPENAI_MODEL',
                          hintText: 'gpt-4.1-mini',
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: _isSaving ? 'Đang lưu...' : 'Lưu .env',
                              icon: Icons.save_rounded,
                              expanded: true,
                              onPressed: _isSaving
                                  ? null
                                  : () => _saveEnv(repository),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: PrimaryButton(
                              label: 'Mở file .env',
                              icon: Icons.description_outlined,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                              onPressed: () => repository.openEnvFile(),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: <Widget>[
              SizedBox(
                width: 420,
                child: SettingsSection(
                  title: 'Đăng nhập 1688',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Text(
                        'Bấm nút bên dưới để backend mở browser 1688. Sau khi bạn đăng nhập thành công, session sẽ được lưu tự động.',
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: _isOpeningSession
                                  ? 'Đang mở browser...'
                                  : 'Mở login 1688',
                              icon: Icons.login_rounded,
                              expanded: true,
                              onPressed: _isOpeningSession
                                  ? null
                                  : _open1688SessionFlow,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: _isSavingSession
                                  ? 'Đang lưu session...'
                                  : 'Lưu session 1688',
                              icon: Icons.save_as_rounded,
                              expanded: true,
                              onPressed: _isSavingSession
                                  ? null
                                  : _save1688Session,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: PrimaryButton(
                              label: 'Kiểm tra lại session',
                              icon: Icons.verified_user_outlined,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                              onPressed: () => ref.invalidate(localSetupStatusProvider),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Mở thư mục session',
                              icon: Icons.folder_open_rounded,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                              onPressed: () => repository.openSessionFolder(),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(
                width: 520,
                child: SettingsSection(
                  title: 'Thao tác nhanh',
                  child: Column(
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: PrimaryButton(
                              label: 'Mở thư mục runtime',
                              icon: Icons.inventory_2_outlined,
                              expanded: true,
                              variant: ButtonVariant.secondary,
                              onPressed: () => repository.openWorkspaceFolder(),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (setupAsync.hasError)
                        Text(
                          'Không đọc được cấu hình local hoặc backend chưa sẵn sàng.',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.error,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _loadControllersFromStatus(SetupStatus setupStatus) {
    _modelController.text = setupStatus.openAiModel;
    ref.read(localSetupRepositoryProvider).loadEnvValues().then((values) {
      if (!mounted) {
        return;
      }
      _zyteController.text = values['ZYTE_API_KEY'] ?? '';
      _openAiController.text = values['OPENAI_API_KEY'] ?? '';
      _modelController.text = values['OPENAI_MODEL'] ?? setupStatus.openAiModel;
      setState(() {});
    });
  }

  StatusBadge _buildStatusBadge({
    required bool ready,
    required String readyText,
    required String missingText,
  }) {
    return StatusBadge(
      ready ? readyText : missingText,
      color: ready ? AppColors.success : AppColors.warning,
    );
  }

  Future<void> _saveEnv(LocalSetupRepository repository) async {
    setState(() {
      _isSaving = true;
      _message = null;
    });
    try {
      await repository.saveEnvValues(
        zyteApiKey: _zyteController.text,
        openAiApiKey: _openAiController.text,
        openAiModel: _modelController.text,
      );
      ref.invalidate(localSetupStatusProvider);
      setState(() {
        _isError = false;
        _message = 'Đã lưu file .env thành công.';
      });
    } catch (error) {
      setState(() {
        _isError = true;
        _message = 'Không lưu được file .env: $error';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _open1688SessionFlow() async {
    setState(() {
      _isOpeningSession = true;
      _message = 'Đang mở browser 1688. Hãy đăng nhập, rồi quay lại app và bấm Lưu session 1688.';
      _isError = false;
    });

    try {
      await ref.read(crawlApiServiceProvider).open1688SessionFlow();
      ref.invalidate(localSetupStatusProvider);
      setState(() {
        _message = 'Browser 1688 đã mở. Sau khi đăng nhập thành công, bấm Lưu session 1688.';
        _isError = false;
      });
    } catch (error) {
      setState(() {
        _message = 'Không mở được login 1688: $error';
        _isError = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isOpeningSession = false;
        });
      }
    }
  }

  Future<void> _save1688Session() async {
    setState(() {
      _isSavingSession = true;
      _message = 'Đang lưu session 1688 từ browser đang mở...';
      _isError = false;
    });

    try {
      await ref.read(crawlApiServiceProvider).save1688Session();
      ref.invalidate(localSetupStatusProvider);
      setState(() {
        _message = 'Đã lưu session 1688 thành công.';
        _isError = false;
      });
    } catch (error) {
      setState(() {
        _message = 'Không lưu được session 1688: $error';
        _isError = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSavingSession = false;
        });
      }
    }
  }
}

class _SetupRow extends StatelessWidget {
  const _SetupRow({
    required this.title,
    required this.subtitle,
    required this.badge,
  });

  final String title;
  final String subtitle;
  final Widget badge;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        badge,
      ],
    );
  }
}
