import 'package:flutter/material.dart';
import '../constants/theme_constants.dart';

class FilterCriteria {
  String searchQuery;
  String source;
  String status;
  String section;

  FilterCriteria({
    this.searchQuery = "",
    this.source = "All",
    this.status = "All",
    this.section = "All",
  });

  bool get isActive =>
      searchQuery.isNotEmpty || source != "All" || status != "All" || section != "All";

  void reset() {
    searchQuery = "";
    source = "All";
    status = "All";
    section = "All";
  }

  FilterCriteria copy() {
    return FilterCriteria(
      searchQuery: searchQuery,
      source: source,
      status: status,
      section: section,
    );
  }
}

class FilterPanel extends StatefulWidget {
  final FilterCriteria criteria;
  final ValueChanged<FilterCriteria> onFiltersChanged;

  const FilterPanel({
    Key? key,
    required this.criteria,
    required this.onFiltersChanged,
  }) : super(key: key);

  @override
  State<FilterPanel> createState() => _FilterPanelState();
}

class _FilterPanelState extends State<FilterPanel> {
  late TextEditingController _searchController;
  late FilterCriteria _currentCriteria;

  final List<String> _sources = ["All", "Ticketing", "Incident"];
  final List<String> _statuses = ["All", "Completed", "In Progress", "Blocked", "Monitoring"];
  final List<String> _sections = ["All", "Completed", "In Progress", "Blockers / Escalations", "Watch-list"];

  @override
  void initState() {
    super.initState();
    _currentCriteria = widget.criteria.copy();
    _searchController = TextEditingController(text: _currentCriteria.searchQuery);
  }

  @override
  void didUpdateWidget(FilterPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.criteria != widget.criteria) {
      _currentCriteria = widget.criteria.copy();
      _searchController.text = _currentCriteria.searchQuery;
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _apply() {
    _currentCriteria.searchQuery = _searchController.text.trim();
    widget.onFiltersChanged(_currentCriteria);
  }

  void _clear() {
    setState(() {
      _currentCriteria.reset();
      _searchController.clear();
    });
    widget.onFiltersChanged(_currentCriteria);
  }

  void _openFilterDialog() {
    FilterCriteria temp = _currentCriteria.copy();
    final searchCtrl = TextEditingController(text: temp.searchQuery);

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: AppColors.card,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: const BorderSide(color: AppColors.border),
          ),
          title: const Row(
            children: [
              Icon(Icons.tune, color: AppColors.primaryAccent, size: 20),
              SizedBox(width: 8),
              Text(
                "FILTERS",
                style: TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                  color: AppColors.textMain,
                ),
              ),
            ],
          ),
          content: SizedBox(
            width: 420,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Source Filter
                  _buildDropdownRow("Source", temp.source, _sources, (val) {
                    setDialogState(() => temp.source = val);
                  }),
                  const SizedBox(height: 14),

                  // Status Filter
                  _buildDropdownRow("Status", temp.status, _statuses, (val) {
                    setDialogState(() => temp.status = val);
                  }),
                  const SizedBox(height: 14),

                  // Section Filter
                  _buildDropdownRow("Section", temp.section, _sections, (val) {
                    setDialogState(() => temp.section = val);
                  }),
                  const SizedBox(height: 14),

                  // Search Field
                  const Text("Search Query", style: TextStyle(color: AppColors.textSecondary, fontSize: 11.5, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: searchCtrl,
                    style: const TextStyle(color: AppColors.textMain, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: "Search record ID or summary...",
                      hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 12.5),
                      filled: true,
                      fillColor: AppColors.inputBackground,
                      prefixIcon: const Icon(Icons.search, size: 18, color: AppColors.textMuted),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.border)),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.primaryAccent)),
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                setDialogState(() {
                  temp.reset();
                  searchCtrl.clear();
                });
              },
              child: const Text("CLEAR", style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w600)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primaryAccent,
                foregroundColor: const Color(0xFF04140D),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: () {
                temp.searchQuery = searchCtrl.text.trim();
                setState(() {
                  _currentCriteria = temp;
                  _searchController.text = temp.searchQuery;
                });
                widget.onFiltersChanged(_currentCriteria);
                Navigator.pop(ctx);
              },
              child: const Text("APPLY FILTERS", style: TextStyle(fontWeight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDropdownRow(String label, String currentVal, List<String> options, ValueChanged<String> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 11.5, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: AppColors.inputBackground,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.border),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: currentVal,
              isExpanded: true,
              dropdownColor: AppColors.card,
              style: const TextStyle(color: AppColors.textMain, fontSize: 13),
              items: options.map((opt) => DropdownMenuItem(value: opt, child: Text(opt))).toList(),
              onChanged: (val) {
                if (val != null) onChanged(val);
              },
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = _currentCriteria.isActive;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: active ? AppColors.borderAccent : AppColors.border),
      ),
      child: Row(
        children: [
          // Quick Search Bar
          Expanded(
            child: TextField(
              controller: _searchController,
              onChanged: (_) => _apply(),
              style: const TextStyle(color: AppColors.textMain, fontSize: 13),
              decoration: InputDecoration(
                hintText: "Search record ID (e.g. TCK-1001) or summary keyword...",
                hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 12.5),
                filled: true,
                fillColor: AppColors.inputBackground,
                prefixIcon: const Icon(Icons.search, size: 18, color: AppColors.textMuted),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                isDense: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.border)),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.primaryAccent)),
              ),
            ),
          ),
          const SizedBox(width: 12),

          // Filters Dialog Button
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: active ? AppColors.primaryAccent : AppColors.textMain,
              backgroundColor: active ? const Color(0x1A00E5A0) : AppColors.secondaryBackground,
              side: BorderSide(color: active ? AppColors.primaryAccent : AppColors.border),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: _openFilterDialog,
            icon: const Icon(Icons.tune, size: 16),
            label: Row(
              children: [
                const Text("FILTERS", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                if (active) ...[
                  const SizedBox(width: 6),
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: AppColors.primaryAccent,
                      shape: BoxShape.circle,
                    ),
                  ),
                ],
              ],
            ),
          ),

          if (active) ...[
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.close, size: 18, color: AppColors.textMuted),
              tooltip: "Clear Filters",
              onPressed: _clear,
            ),
          ],
        ],
      ),
    );
  }
}
