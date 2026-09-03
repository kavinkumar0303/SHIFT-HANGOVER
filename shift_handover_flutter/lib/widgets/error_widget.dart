import 'package:flutter/material.dart';
import '../constants/theme_constants.dart';

class HandoverErrorWidget extends StatelessWidget {
  final String errorMessage;
  final VoidCallback onRetry;

  const HandoverErrorWidget({
    Key? key,
    required this.errorMessage,
    required this.onRetry,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0x1AFF5C5C),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0x66FF5C5C)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.error_outline, color: AppColors.blockers, size: 20),
              SizedBox(width: 8),
              Text(
                "OPERATION FAILED",
                style: TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: AppColors.blockers,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            errorMessage,
            style: const TextStyle(
              fontSize: 13,
              color: AppColors.textMain,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.blockers,
              foregroundColor: AppColors.textMain,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            ),
            onPressed: onRetry,
            icon: const Icon(Icons.refresh, size: 16),
            label: const Text("Retry Pipeline", style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
