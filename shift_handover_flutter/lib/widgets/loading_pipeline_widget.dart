import 'package:flutter/material.dart';
import '../constants/theme_constants.dart';

class LoadingPipelineWidget extends StatelessWidget {
  final int currentStep; // 0 to 4

  const LoadingPipelineWidget({
    Key? key,
    this.currentStep = 2,
  }) : super(key: key);

  static const List<String> steps = [
    "Fetching activity...",
    "Filtering shift...",
    "Deduplicating...",
    "Generating handover...",
    "Publishing PDF...",
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0x0D00E5A0),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderAccent),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: AppColors.primaryAccent,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                "PIPELINE EXECUTING: ${steps[currentStep.clamp(0, steps.length - 1)]}",
                style: const TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryAccent,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          LayoutBuilder(
            builder: (context, constraints) {
              return Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(steps.length, (index) {
                  final isDone = index < currentStep;
                  final isCurrent = index == currentStep;
                  final label = steps[index].replaceAll("...", "");

                  return Expanded(
                    child: Row(
                      children: [
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 26,
                              height: 26,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: isCurrent
                                    ? AppColors.primaryAccent
                                    : (isDone ? const Color(0x3300E5A0) : AppColors.secondaryBackground),
                                border: Border.all(
                                  color: (isDone || isCurrent) ? AppColors.primaryAccent : AppColors.border,
                                ),
                              ),
                              child: Center(
                                child: isDone
                                    ? const Icon(Icons.check, size: 14, color: AppColors.primaryAccent)
                                    : Text(
                                        "${index + 1}",
                                        style: TextStyle(
                                          fontFamily: AppTypography.fontFamilyMono,
                                          fontSize: 11,
                                          fontWeight: FontWeight.w700,
                                          color: isCurrent ? const Color(0xFF04140D) : AppColors.textSecondary,
                                        ),
                                      ),
                              ),
                            ),
                            const SizedBox(height: 6),
                            if (constraints.maxWidth > 500)
                              Text(
                                label,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: isCurrent ? FontWeight.w700 : FontWeight.w500,
                                  color: isCurrent ? AppColors.textMain : AppColors.textMuted,
                                ),
                              ),
                          ],
                        ),
                        if (index < steps.length - 1)
                          Expanded(
                            child: Container(
                              height: 1.5,
                              color: isDone ? AppColors.primaryAccent : AppColors.border,
                              margin: const EdgeInsets.symmetric(horizontal: 4),
                            ),
                          ),
                      ],
                    ),
                  );
                }),
              );
            },
          ),
        ],
      ),
    );
  }
}
