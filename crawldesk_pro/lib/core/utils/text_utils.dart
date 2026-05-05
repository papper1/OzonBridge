import 'dart:convert';

String sanitizeDisplayText(String value) {
  final input = value.trim();
  if (input.isEmpty) {
    return input;
  }
  final repaired = _tryRepairLatin1Utf8(input);
  return repaired.isNotEmpty ? repaired : input;
}

String _tryRepairLatin1Utf8(String input) {
  final hasMojibakeHint = input.contains('Ã') ||
      input.contains('Ä') ||
      input.contains('Å') ||
      input.contains('áº') ||
      input.contains('âœ');
  if (!hasMojibakeHint) {
    return input;
  }
  try {
    return utf8.decode(latin1.encode(input), allowMalformed: true);
  } catch (_) {
    return input;
  }
}
