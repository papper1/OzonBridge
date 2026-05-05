import 'package:flutter/material.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    required this.label,
    super.key,
    this.onPressed,
    this.icon,
    this.expanded = false,
    this.variant = ButtonVariant.primary,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool expanded;
  final ButtonVariant variant;

  @override
  Widget build(BuildContext context) {
    final child = variant == ButtonVariant.primary
        ? FilledButton.icon(
            onPressed: onPressed,
            icon: icon == null ? const SizedBox.shrink() : Icon(icon, size: 18),
            label: Text(label),
          )
        : OutlinedButton.icon(
            onPressed: onPressed,
            icon: icon == null ? const SizedBox.shrink() : Icon(icon, size: 18),
            label: Text(label),
          );

    if (expanded) {
      return SizedBox(width: double.infinity, child: child);
    }
    return child;
  }
}

enum ButtonVariant { primary, secondary }
