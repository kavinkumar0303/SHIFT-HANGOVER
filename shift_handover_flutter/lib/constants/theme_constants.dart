import 'package:flutter/material.dart';

class AppColors {
  // Obsidian + Electric Mint Theme Palette
  static const Color background = Color(0xFF070B0A);
  static const Color secondaryBackground = Color(0xFF0D1412);
  static const Color card = Color(0xFF121C19);
  static const Color cardHover = Color(0xFF172722);
  static const Color inputBackground = Color(0xFF0A110F);

  static const Color primaryAccent = Color(0xFF00E5A0);
  static const Color brightAccent = Color(0xFF5CFFC1);
  static const Color accentGlow = Color(0x2600E5A0);

  static const Color completed = Color(0xFF00D68F);
  static const Color inProgress = Color(0xFF38BDF8);
  static const Color blockers = Color(0xFFFF5C5C);
  static const Color watchList = Color(0xFFFFC857);

  static const Color textMain = Color(0xFFF1F5F3);
  static const Color textSecondary = Color(0xFF8FA39C);
  static const Color textMuted = Color(0xFF5C726A);

  static const Color border = Color(0xFF20332D);
  static const Color borderHover = Color(0xFF2F4D44);
  static const Color borderAccent = Color(0x5900E5A0);
}

class AppTypography {
  static const String fontFamilySans = 'Plus Jakarta Sans';
  static const String fontFamilyMono = 'JetBrains Mono';

  static const TextStyle brandTitle = TextStyle(
    fontFamily: fontFamilyMono,
    fontWeight: FontWeight.w700,
    fontSize: 16,
    color: AppColors.textMain,
    letterSpacing: 0.5,
  );

  static const TextStyle pageTitle = TextStyle(
    fontFamily: fontFamilyMono,
    fontWeight: FontWeight.w700,
    fontSize: 22,
    color: AppColors.textMain,
    letterSpacing: -0.5,
  );

  static const TextStyle sectionTitle = TextStyle(
    fontFamily: fontFamilyMono,
    fontWeight: FontWeight.w700,
    fontSize: 13,
    letterSpacing: 0.5,
  );

  static const TextStyle codeText = TextStyle(
    fontFamily: fontFamilyMono,
    fontSize: 12,
    color: AppColors.textSecondary,
  );
}
