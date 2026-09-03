import 'package:flutter/material.dart';
import '../constants/theme_constants.dart';
import '../models/handover_models.dart';

class SourceStatusWidget extends StatelessWidget {
  final List<SourceStatus> sources;
  final bool isLoading;
  final VoidCallback onRefresh;

  const SourceStatusWidget({
    Key? key,
    required this.sources,
    required this.isLoading,
    required this.onRefresh,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Row(
              children: [
                Icon(Icons.storage, size: 16, color: AppColors.primaryAccent),
                SizedBox(width: 8),
                Text(
                  "LIVE DATA SOURCE CONNECTIONS",
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textSecondary,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
            TextButton.icon(
              onPressed: isLoading ? null : onRefresh,
              icon: isLoading
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primaryAccent),
                    )
                  : const Icon(Icons.refresh, size: 14, color: AppColors.textSecondary),
              label: const Text(
                "Refresh Status",
                style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth > 650;
            return isWide
                ? Row(
                    children: [
                      Expanded(child: _buildSourceCard(_findSource("Ticketing", "Jira Feed", "data/tickets.json"))),
                      const SizedBox(width: 16),
                      Expanded(child: _buildSourceCard(_findSource("Incident", "PagerDuty Alerts", "data/incidents.json"))),
                    ],
                  )
                : Column(
                    children: [
                      _buildSourceCard(_findSource("Ticketing", "Jira Feed", "data/tickets.json")),
                      const SizedBox(height: 12),
                      _buildSourceCard(_findSource("Incident", "PagerDuty Alerts", "data/incidents.json")),
                    ],
                  );
          },
        ),
      ],
    );
  }

  SourceStatus _findSource(String match, String fallbackName, String fallbackPath) {
    return sources.firstWhere(
      (s) => s.name.toLowerCase().contains(match.toLowerCase()),
      orElse: () => SourceStatus(
        name: fallbackName,
        path: fallbackPath,
        connected: false,
        status: "Checking...",
        totalRecords: 0,
      ),
    );
  }

  Widget _buildSourceCard(SourceStatus source) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(
                    source.name.toLowerCase().contains("ticket") ? Icons.confirmation_number_outlined : Icons.shield_outlined,
                    size: 18,
                    color: AppColors.primaryAccent,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    source.name,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: AppColors.textMain,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: source.connected ? const Color(0x1F00E5A0) : const Color(0x1FFF5C5C),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: source.connected ? const Color(0x4D00E5A0) : const Color(0x4DFF5C5C),
                  ),
                ),
                child: Text(
                  source.connected ? "● Connected" : "● Unavailable",
                  style: TextStyle(
                    fontFamily: AppTypography.fontFamilyMono,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    color: source.connected ? AppColors.primaryAccent : AppColors.blockers,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("Records Available:", style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
              Text(
                "${source.totalRecords} records",
                style: const TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                  color: AppColors.textMain,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("Data Path:", style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
              Text(
                source.path,
                style: const TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontSize: 11,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
