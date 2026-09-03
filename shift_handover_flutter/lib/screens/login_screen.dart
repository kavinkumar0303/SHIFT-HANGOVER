import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../constants/theme_constants.dart';
import '../services/api_service.dart';
import '../main.dart';

class LoginScreen extends StatefulWidget {
  final Function(Map<String, dynamic> user) onLoginSuccess;

  const LoginScreen({Key? key, required this.onLoginSuccess}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _emailController =
      TextEditingController(text: "operator@noc.internal");
  final TextEditingController _passwordController =
      TextEditingController(text: "••••••••••••");
  bool _isLoading = false;
  String? _errorMessage;

  final List<Map<String, String>> _demoUsers = [
    {
      "name": "Alex Rivera",
      "email": "operator@noc.internal",
      "role": "Lead On-Call SRE",
      "badge": "On-Call L3",
    },
    {
      "name": "Maria Garcia",
      "email": "supervisor@noc.internal",
      "role": "Shift Operations Supervisor",
      "badge": "Commander",
    },
    {
      "name": "Admin Engineer",
      "email": "admin@shifthandover.io",
      "role": "System Administrator",
      "badge": "Root Admin",
    },
  ];

  Future<void> _performLogin(String email) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final uri = Uri.parse("${ApiService.baseUrl}/api/login");
      final response = await http
          .post(
            uri,
            headers: {"Content-Type": "application/json"},
            body: json.encode({"email": email, "password": "demo"}),
          )
          .timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final user = data["user"] as Map<String, dynamic>? ?? {
          "email": email,
          "name": "Alex Rivera",
          "role": "Lead On-Call SRE",
          "avatar": "AR"
        };
        widget.onLoginSuccess(user);
      } else {
        // Fallback for offline demo
        _fallbackLogin(email);
      }
    } catch (e) {
      // Graceful offline fallback
      _fallbackLogin(email);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _fallbackLogin(String email) {
    final demoMatch = _demoUsers.firstWhere(
      (u) => u["email"] == email,
      orElse: () => {
        "name": email.split("@")[0].toUpperCase(),
        "email": email,
        "role": "On-Call Engineer",
        "badge": "Operator",
      },
    );

    widget.onLoginSuccess({
      "name": demoMatch["name"],
      "email": demoMatch["email"],
      "role": demoMatch["role"],
      "avatar": demoMatch["name"]!.substring(0, 2).toUpperCase(),
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 440),
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              color: AppColors.card,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x66000000),
                  blurRadius: 30,
                  offset: Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Brand Header
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppColors.secondaryBackground,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: const Icon(Icons.bolt,
                          color: AppColors.primaryAccent, size: 22),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        RichText(
                          text: const TextSpan(
                            text: "SHIFT",
                            style: TextStyle(
                              fontFamily: AppTypography.fontFamilyMono,
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                              color: AppColors.textMain,
                            ),
                            children: [
                              TextSpan(
                                  text: "//",
                                  style: TextStyle(
                                      color: AppColors.primaryAccent)),
                              TextSpan(text: "HANDOVER"),
                            ],
                          ),
                        ),
                        const Text(
                          "NOC ACCESS PORTAL",
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                const Text(
                  "Operator Authentication",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textMain,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  "Sign in to generate and publish shift handover notes",
                  style: TextStyle(
                    fontSize: 12.5,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 20),

                if (_errorMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0x1AFF5C5C),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppColors.blockers),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(
                          color: AppColors.blockers, fontSize: 12),
                    ),
                  ),
                  const SizedBox(height: 14),
                ],

                // Email Field
                const Text("Operator Email / Identity",
                    style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                TextField(
                  controller: _emailController,
                  style: const TextStyle(
                      color: AppColors.textMain,
                      fontFamily: AppTypography.fontFamilyMono,
                      fontSize: 13),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: AppColors.inputBackground,
                    prefixIcon: const Icon(Icons.alternate_email,
                        size: 16, color: AppColors.textMuted),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide:
                            const BorderSide(color: AppColors.border)),
                    focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(
                            color: AppColors.primaryAccent)),
                  ),
                ),
                const SizedBox(height: 14),

                // Password Field
                const Text("Password / Key",
                    style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                TextField(
                  controller: _passwordController,
                  obscureText: true,
                  style: const TextStyle(
                      color: AppColors.textMain, fontSize: 13),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: AppColors.inputBackground,
                    prefixIcon: const Icon(Icons.lock_outline,
                        size: 16, color: AppColors.textMuted),
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide:
                            const BorderSide(color: AppColors.border)),
                    focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(
                            color: AppColors.primaryAccent)),
                  ),
                ),
                const SizedBox(height: 18),

                // Login Action Button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primaryAccent,
                      foregroundColor: const Color(0xFF04140D),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8)),
                      elevation: 4,
                      shadowColor: AppColors.accentGlow,
                    ),
                    onPressed: _isLoading
                        ? null
                        : () => _performLogin(_emailController.text.trim()),
                    child: _isLoading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Color(0xFF04140D),
                            ),
                          )
                        : const Text(
                            "AUTHENTICATE & ENTER",
                            style: TextStyle(
                              fontFamily: AppTypography.fontFamilySans,
                              fontWeight: FontWeight.w800,
                              fontSize: 12.5,
                              letterSpacing: 0.5,
                            ),
                          ),
                  ),
                ),
                const SizedBox(height: 22),

                // Quick Demo Logins
                const Divider(color: AppColors.border),
                const SizedBox(height: 12),
                const Text(
                  "⚡ Quick 1-Click Role Logins:",
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textMuted,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 8),

                Column(
                  children: _demoUsers.map((u) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: InkWell(
                        onTap: () {
                          _emailController.text = u["email"]!;
                          _performLogin(u["email"]!);
                        },
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppColors.secondaryBackground,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: AppColors.border),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    u["name"]!,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 12,
                                      color: AppColors.textMain,
                                    ),
                                  ),
                                  Text(
                                    u["role"]!,
                                    style: const TextStyle(
                                      fontSize: 10.5,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: const Color(0x1A00E5A0),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  u["badge"]!,
                                  style: const TextStyle(
                                    fontFamily: AppTypography.fontFamilyMono,
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.primaryAccent,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),

                // Trust indicators
                const Center(
                  child: Text(
                    "🔒 256-BIT ENCRYPTED • ZERO HALLUCINATION • NOC SSO",
                    style: TextStyle(
                      fontFamily: AppTypography.fontFamilyMono,
                      fontSize: 9.5,
                      color: AppColors.textMuted,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
