import 'package:flutter/material.dart';
import '../constants/theme_constants.dart';
import '../models/handover_models.dart';
import 'filter_panel.dart';

class HandoverSectionsWidget extends StatelessWidget {
  final HandoverResponse response;
  final FilterCriteria filterCriteria;

  const HandoverSectionsWidget({
    Key? key,
    required this.response,
    required this.filterCriteria,
  }) : super(key: key);

  List<HandoverItem> _filterItems(List<HandoverItem> items, String sectionName) {
    // 1. Section Filter
    if (filterCriteria.section != "All") {
      final normFilterSec = filterCriteria.section.toLowerCase();
      final normSec = sectionName.toLowerCase();
      if (!normSec.contains(normFilterSec) && !normFilterSec.contains(normSec)) {
        return [];
      }
    }

    return items.where((item) {
      // 2. Source Filter
      if (filterCriteria.source != "All") {
        if (!item.source.toLowerCase().contains(filterCriteria.source.toLowerCase())) {
          return false;
        }
      }

      // 3. Status Filter
      if (filterCriteria.status != "All") {
        final normFilterStatus = filterCriteria.status.toLowerCase().replaceAll(" ", "_");
        final normItemStatus = item.status.toLowerCase().replaceAll(" ", "_");
        if (!normItemStatus.contains(normFilterStatus) && !normFilterStatus.contains(normItemStatus)) {
          return false;
        }
      }

      // 4. Search Query (Record ID or Summary)
      if (filterCriteria.searchQuery.isNotEmpty) {
        final query = filterCriteria.searchQuery.toLowerCase();
        final matchId = item.recordId.toLowerCase().contains(query);
        final matchSummary = item.summary.toLowerCase().contains(query);
        final matchDetails = item.details?.toLowerCase().contains(query) ?? false;
        if (!matchId && !matchSummary && !matchDetails) {
          return false;
        }
      }

      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final filteredCompleted = _filterItems(response.completed, "COMPLETED");
    final filteredInProgress = _filterItems(response.inProgress, "IN PROGRESS");
    final filteredBlockers = _filterItems(response.blockers, "BLOCKERS / ESCALATIONS");
    final filteredWatchList = _filterItems(response.watchList, "WATCH-LIST");

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // KPI Summary Metric Counters
        _buildMetricCounters(
          completed: filteredCompleted.length,
          inProgress: filteredInProgress.length,
          blockers: filteredBlockers.length,
          watchList: filteredWatchList.length,
        ),
        const SizedBox(height: 22),

        // 4 Structured Sections
        _buildSectionCard(
          title: "COMPLETED",
          iconText: "✓",
          color: AppColors.completed,
          items: filteredCompleted,
        ),
        const SizedBox(height: 16),

        _buildSectionCard(
          title: "IN PROGRESS",
          iconText: "◐",
          color: AppColors.inProgress,
          items: filteredInProgress,
        ),
        const SizedBox(height: 16),

        _buildSectionCard(
          title: "BLOCKERS / ESCALATIONS",
          iconText: "⚠",
          color: AppColors.blockers,
          items: filteredBlockers,
        ),
        const SizedBox(height: 16),

        _buildSectionCard(
          title: "WATCH-LIST",
          iconText: "◉",
          color: AppColors.watchList,
          items: filteredWatchList,
        ),
      ],
    );
  }

  Widget _buildMetricCounters({
    required int completed,
    required int inProgress,
    required int blockers,
    required int watchList,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 600;
        final cardWidth = isWide ? (constraints.maxWidth - 36) / 4 : (constraints.maxWidth - 12) / 2;

        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _buildMetricTile("COMPLETED", completed, AppColors.completed, cardWidth),
            _buildMetricTile("IN PROGRESS", inProgress, AppColors.inProgress, cardWidth),
            _buildMetricTile("BLOCKERS", blockers, AppColors.blockers, cardWidth),
            _buildMetricTile("WATCH-LIST", watchList, AppColors.watchList, cardWidth),
          ],
        );
      },
    );
  }

  Widget _buildMetricTile(String label, int count, Color color, double width) {
    return Container(
      width: width,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(color: color, width: 3),
          top: const BorderSide(color: AppColors.border),
          right: const BorderSide(color: AppColors.border),
          bottom: const BorderSide(color: AppColors.border),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
          const SizedBox(height: 2),
          Text(
            "$count",
            style: TextStyle(
              fontFamily: AppTypography.fontFamilyMono,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required String iconText,
    required Color color,
    required List<HandoverItem> items,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Section Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.08),
              border: const Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(iconText, style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.w800)),
                    const SizedBox(width: 10),
                    Text(
                      title,
                      style: TextStyle(
                        fontFamily: AppTypography.fontFamilyMono,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: color,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.secondaryBackground,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Text(
                    "${items.length} item(s)",
                    style: const TextStyle(
                      fontFamily: AppTypography.fontFamilyMono,
                      fontSize: 11,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Section Body
          Padding(
            padding: const EdgeInsets.all(14),
            child: items.isEmpty
                ? Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: AppColors.secondaryBackground,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppColors.border, style: BorderStyle.solid),
                    ),
                    child: const Center(
                      child: Text(
                        "Nothing to report.",
                        style: TextStyle(
                          fontStyle: FontStyle.italic,
                          color: AppColors.textMuted,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  )
                : Column(
                    children: items.map((item) => _buildItemCard(item)).toList(),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildItemCard(HandoverItem item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.secondaryBackground,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top Row: Record ID, Summary, Source & Timestamp Traceability
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0x1A00E5A0),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0x4D00E5A0)),
                ),
                child: Text(
                  "[${item.recordId}]",
                  style: const TextStyle(
                    fontFamily: AppTypography.fontFamilyMono,
                    fontWeight: FontWeight.w700,
                    fontSize: 11.5,
                    color: AppColors.primaryAccent,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  item.summary,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13.5,
                    color: AppColors.textMain,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                "${item.source} | ${item.timestamp}",
                style: const TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontSize: 11,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Badges Row
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _buildBadge(item.status.toUpperCase(), const Color(0x1AFFFFFF), AppColors.textMain),
              if (item.priority != null && item.priority!.isNotEmpty)
                _buildBadge(item.priority!, const Color(0x1AFF5C5C), AppColors.blockers),
              if (item.assignee != null && item.assignee!.isNotEmpty)
                _buildBadge(item.assignee!, const Color(0x1A38BDF8), AppColors.inProgress),
            ],
          ),

          // Details text
          if (item.details != null && item.details!.isNotEmpty && item.details != item.summary) ...[
            const SizedBox(height: 8),
            Text(
              item.details!,
              style: const TextStyle(
                fontSize: 12.5,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ],

          // Progression Trail
          if (item.progression.length > 1) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.background,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  const Text("Progression: ", style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                  Expanded(
                    child: Text(
                      item.progression.join("  →  "),
                      style: const TextStyle(
                        fontFamily: AppTypography.fontFamilyMono,
                        fontSize: 11,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBadge(String text, Color bg, Color textCol) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: textCol.withOpacity(0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontFamily: AppTypography.fontFamilyMono,
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: textCol,
        ),
      ),
    );
  }
}
