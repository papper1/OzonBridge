import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../constants/app_colors.dart';
import '../constants/app_sizes.dart';

class SidebarItemData {
  const SidebarItemData(this.label, this.icon, this.route);

  final String label;
  final IconData icon;
  final String route;
}

const List<SidebarItemData> sidebarItems = <SidebarItemData>[
  SidebarItemData('Tổng quan', Icons.home_rounded, '/'),
  SidebarItemData('Thu thập dữ liệu', Icons.cloud_download_outlined, '/crawl'),
  SidebarItemData('Template', Icons.description_outlined, '/templates'),
  SidebarItemData('Kết quả', Icons.analytics_outlined, '/results'),
  SidebarItemData('Cài đặt', Icons.settings_outlined, '/settings'),
];

class AppSidebar extends StatelessWidget {
  const AppSidebar({required this.collapsed, super.key});

  final bool collapsed;

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();
    return Container(
      width: collapsed ? AppSizes.sidebarCollapsed : AppSizes.sidebarExpanded,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(right: BorderSide(color: AppColors.border)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          children: <Widget>[
            Row(
              children: <Widget>[
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: <Color>[AppColors.primary, AppColors.primaryAlt],
                    ),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.blur_on_rounded, color: Colors.white),
                ),
                if (!collapsed) ...<Widget>[
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'CrawlDesk Pro',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Crawl tool cá nhân',
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 28),
            Expanded(
              child: ListView.separated(
                itemCount: sidebarItems.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (BuildContext context, int index) {
                  final item = sidebarItems[index];
                  final selected = location == item.route;
                  return InkWell(
                    onTap: () => context.go(item.route),
                    borderRadius: BorderRadius.circular(16),
                    child: Container(
                      padding: EdgeInsets.symmetric(
                        horizontal: collapsed ? 0 : 14,
                        vertical: 14,
                      ),
                      decoration: BoxDecoration(
                        color: selected
                            ? AppColors.primarySoft
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        mainAxisAlignment: collapsed
                            ? MainAxisAlignment.center
                            : MainAxisAlignment.start,
                        children: <Widget>[
                          Icon(
                            item.icon,
                            color: selected
                                ? AppColors.primary
                                : AppColors.textSecondary,
                          ),
                          if (!collapsed) ...<Widget>[
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                item.label,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: selected
                                      ? AppColors.primary
                                      : AppColors.textPrimary,
                                  fontWeight: selected
                                      ? FontWeight.w700
                                      : FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
