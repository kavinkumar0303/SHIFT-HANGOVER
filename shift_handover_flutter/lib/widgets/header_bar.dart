import 'dart:async';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../constants/theme_constants.dart';
import '../services/api_service.dart';

class HeaderBar extends StatefulWidget {
  final VoidCallback? onSettingsTap;
  final Map<String, dynamic>? currentUser;
  final VoidCallback? onLogout;

  const HeaderBar({
    Key? key,
    this.onSettingsTap,
    this.currentUser,
    this.onLogout,
  }) : super(key: key);

  @override
  State<HeaderBar> createState() => _HeaderBarState();
}

class _HeaderBarState extends State<HeaderBar> {
  late Timer _clockTimer;
  String _utcTimeString = "";

  @override
  void initState() {
    super.initState();
    _updateTime();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) => _updateTime());
  }

  void _updateTime() {
    final now = DateTime.now().toUtc();
    if (mounted) {
      setState(() {
        _utcTimeString = "${DateFormat('HH:mm:ss').format(now)} UTC";
      });
    }
  }

  @override
  void dispose() {
    _clockTimer.cancel();
    super.dispose();
  }

  void _showBackendConfigDialog() {
    final controller = TextEditingController(text: ApiService.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.card,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.border),
        ),
        title: const Text("Configure Python Backend URL", style: TextStyle(color: AppColors.textMain, fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Set the endpoint URL for the Python Shift Handover backend:",
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              style: const TextStyle(color: AppColors.textMain, fontFamily: AppTypography.fontFamilyMono, fontSize: 13),
              decoration: InputDecoration(
                filled: true,
                fillColor: AppColors.inputBackground,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.border),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.primaryAccent),
                ),
                hintText: "http://localhost:5050",
                hintStyle: const TextStyle(color: AppColors.textMuted),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Cancel", style: TextStyle(color: AppColors.textSecondary)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primaryAccent,
              foregroundColor: const Color(0xFF04140D),
            ),
            onPressed: () {
              ApiService.baseUrl = controller.text.trim();
              Navigator.pop(ctx);
              if (widget.onSettingsTap != null) widget.onSettingsTap!();
            },
            child: const Text("Save URL"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
      decoration: const BoxDecoration(
        color: AppColors.secondaryBackground,
        border: Border(bottom: BorderSide(color: AppColors.border, width: 1)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Brand Logo & Title
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.border),
                ),
                child: const Icon(Icons.bolt, color: AppColors.primaryAccent, size: 22),
              ),
              const SizedBox(width: 14),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  RichText(
                    text: const TextSpan(
                      text: "SHIFT",
                      style: TextStyle(
                        fontFamily: AppTypography.fontFamilyMono,
                        fontWeight: FontWeight.w800,
                        fontSize: 18,
                        color: AppColors.textMain,
                        letterSpacing: 0.5,
                      ),
                      children: [
                        TextSpan(text: "//", style: TextStyle(color: AppColors.primaryAccent)),
                        TextSpan(text: "HANDOVER"),
                      ],
                    ),
                  ),
                  const Text(
                    "Automated Shift Handover Intelligence",
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),

          // Status, User Profile & Clock
          Row(
            children: [
              // User Profile Pill (if logged in)
              if (widget.currentUser != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.card,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 12,
                        backgroundColor: const Color(0x3300E5A0),
                        child: Text(
                          widget.currentUser!["avatar"] ?? "OP",
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primaryAccent,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            widget.currentUser!["name"] ?? "Operator",
                            style: const TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textMain,
                            ),
                          ),
                          Text(
                            widget.currentUser!["role"] ?? "On-Call SRE",
                            style: const TextStyle(
                              fontSize: 9.5,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                      if (widget.onLogout != null) ...[
                        const SizedBox(width: 8),
                        IconButton(
                          icon: const Icon(Icons.logout, size: 14, color: AppColors.textMuted),
                          tooltip: "Logout / Switch Operator",
                          onPressed: widget.onLogout,
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 14),
              ],

              // System Ready Pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0x1A00E5A0),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.primaryAccent, width: 1),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: AppColors.primaryAccent,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(color: AppColors.primaryAccent, blurRadius: 6, spreadRadius: 1),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text(
                      "SYSTEM READY",
                      style: TextStyle(
                        fontFamily: AppTypography.fontFamilyMono,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: AppColors.primaryAccent,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),

              // Live UTC Clock
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.border),
                ),
                child: Text(
                  _utcTimeString,
                  style: const TextStyle(
                    fontFamily: AppTypography.fontFamilyMono,
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
              const SizedBox(width: 12),

              // API Endpoint Settings Button
              IconButton(
                icon: const Icon(Icons.settings, color: AppColors.textSecondary, size: 20),
                tooltip: "Backend Settings",
                onPressed: _showBackendConfigDialog,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
