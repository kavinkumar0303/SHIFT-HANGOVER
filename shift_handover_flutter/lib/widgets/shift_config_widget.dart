import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../constants/theme_constants.dart';

class ShiftConfigWidget extends StatefulWidget {
  final Function(String shiftStart, String shiftEnd, bool dummy) onGenerate;
  final bool isLoading;

  const ShiftConfigWidget({
    Key? key,
    required this.onGenerate,
    required this.isLoading,
  }) : super(key: key);

  @override
  State<ShiftConfigWidget> createState() => _ShiftConfigWidgetState();
}

class _ShiftConfigWidgetState extends State<ShiftConfigWidget> {
  DateTime _startDate = DateTime(2026, 9, 3, 17, 0);
  DateTime _endDate = DateTime(2026, 9, 3, 20, 0);
  String _selectedTz = "+05:30";
  String _activePreset = "Primary Demo";

  final List<Map<String, dynamic>> _presets = [
    {
      "name": "Primary Demo",
      "label": "Primary Demo (17:00 – 20:00 IST)",
      "start": DateTime(2026, 9, 3, 17, 0),
      "end": DateTime(2026, 9, 3, 20, 0),
      "tz": "+05:30",
    },
    {
      "name": "Night Shift",
      "label": "Night Shift (20:00 – 04:00 IST)",
      "start": DateTime(2026, 9, 3, 20, 0),
      "end": DateTime(2026, 9, 4, 4, 0),
      "tz": "+05:30",
    },
    {
      "name": "Early Morning",
      "label": "Early Morning (04:00 – 12:00 IST)",
      "start": DateTime(2026, 9, 4, 4, 0),
      "end": DateTime(2026, 9, 4, 12, 0),
      "tz": "+05:30",
    },
    {
      "name": "Blocker Shift",
      "label": "Blocker Shift (12:00 – 16:00 IST)",
      "start": DateTime(2026, 9, 4, 12, 0),
      "end": DateTime(2026, 9, 4, 16, 0),
      "tz": "+05:30",
    },
    {
      "name": "Quiet Shift",
      "label": "Quiet Shift (16:00 – 18:00 IST)",
      "start": DateTime(2026, 9, 4, 16, 0),
      "end": DateTime(2026, 9, 4, 18, 0),
      "tz": "+05:30",
    },
    {
      "name": "Empty Window",
      "label": "Empty Window (Nothing to report)",
      "start": DateTime(2026, 9, 5, 0, 0),
      "end": DateTime(2026, 9, 5, 4, 0),
      "tz": "+05:30",
    },
  ];

  void _selectPreset(Map<String, dynamic> preset) {
    setState(() {
      _activePreset = preset["name"];
      _startDate = preset["start"];
      _endDate = preset["end"];
      _selectedTz = preset["tz"];
    });
  }

  Future<void> _pickDateTime(bool isStart) async {
    final current = isStart ? _startDate : _endDate;

    final pickedDate = await showDatePicker(
      context: context,
      initialDate: current,
      firstDate: DateTime(2025),
      lastDate: DateTime(2030),
      builder: (context, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(
            primary: AppColors.primaryAccent,
            onPrimary: Color(0xFF04140D),
            surface: AppColors.card,
            onSurface: AppColors.textMain,
          ),
          dialogBackgroundColor: AppColors.card,
        ),
        child: child!,
      ),
    );

    if (pickedDate == null) return;

    final pickedTime = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(current),
      builder: (context, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(
            primary: AppColors.primaryAccent,
            onPrimary: Color(0xFF04140D),
            surface: AppColors.card,
            onSurface: AppColors.textMain,
          ),
          dialogBackgroundColor: AppColors.card,
        ),
        child: child!,
      ),
    );

    if (pickedTime == null) return;

    final combined = DateTime(
      pickedDate.year,
      pickedDate.month,
      pickedDate.day,
      pickedTime.hour,
      pickedTime.minute,
    );

    setState(() {
      _activePreset = "Custom";
      if (isStart) {
        _startDate = combined;
      } else {
        _endDate = combined;
      }
    });
  }

  String _formatIso(DateTime dt) {
    final formatted = DateFormat("yyyy-MM-dd'T'HH:mm:ss").format(dt);
    return "$formatted$_selectedTz";
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          const Row(
            children: [
              Icon(Icons.schedule, color: AppColors.primaryAccent, size: 20),
              SizedBox(width: 10),
              Text(
                "DEFINE SHIFT WINDOW",
                style: TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                  color: AppColors.textMain,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            "Events strictly filtered to half-open interval [shift_start, shift_end)",
            style: TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          const SizedBox(height: 18),

          // Preset Chips
          const Text("Quick Shift Presets:", style: TextStyle(color: AppColors.textSecondary, fontSize: 11, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _presets.map((p) {
              final isSelected = _activePreset == p["name"];
              return InkWell(
                onTap: () => _selectPreset(p),
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: isSelected ? const Color(0x1A00E5A0) : AppColors.secondaryBackground,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: isSelected ? AppColors.primaryAccent : AppColors.border,
                      width: 1,
                    ),
                  ),
                  child: Text(
                    p["label"],
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                      color: isSelected ? AppColors.primaryAccent : AppColors.textSecondary,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),

          // Inputs Row
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth > 700;
              return isWide
                  ? Row(
                      children: [
                        Expanded(child: _buildPickerField("Shift Start", _startDate, () => _pickDateTime(true))),
                        const SizedBox(width: 14),
                        Expanded(child: _buildPickerField("Shift End", _endDate, () => _pickDateTime(false))),
                        const SizedBox(width: 14),
                        SizedBox(width: 160, child: _buildTimezoneDropdown()),
                      ],
                    )
                  : Column(
                      children: [
                        _buildPickerField("Shift Start", _startDate, () => _pickDateTime(true)),
                        const SizedBox(height: 12),
                        _buildPickerField("Shift End", _endDate, () => _pickDateTime(false)),
                        const SizedBox(height: 12),
                        _buildTimezoneDropdown(),
                      ],
                    );
            },
          ),
          const SizedBox(height: 22),

          // Actions Row
          Wrap(
            spacing: 12,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              // Main Action Button
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primaryAccent,
                  foregroundColor: const Color(0xFF04140D),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  elevation: 4,
                  shadowColor: AppColors.accentGlow,
                ),
                onPressed: widget.isLoading
                    ? null
                    : () => widget.onGenerate(_formatIso(_startDate), _formatIso(_endDate), false),
                icon: widget.isLoading
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF04140D)))
                    : const Icon(Icons.play_arrow, size: 18),
                label: const Text(
                  "GENERATE HANDOVER",
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13, letterSpacing: 0.5),
                ),
              ),

              // Dummy Pipeline Test
              OutlinedButton(
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textMain,
                  side: const BorderSide(color: AppColors.border),
                  backgroundColor: AppColors.secondaryBackground,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: widget.isLoading
                    ? null
                    : () => widget.onGenerate(_formatIso(_startDate), _formatIso(_endDate), true),
                child: const Text("Run Dummy Pipeline Test", style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPickerField(String label, DateTime dt, VoidCallback onTap) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 11.5, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            decoration: BoxDecoration(
              color: AppColors.inputBackground,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  DateFormat("yyyy-MM-dd HH:mm").format(dt),
                  style: const TextStyle(
                    fontFamily: AppTypography.fontFamilyMono,
                    fontSize: 13,
                    color: AppColors.textMain,
                  ),
                ),
                const Icon(Icons.calendar_today, size: 14, color: AppColors.primaryAccent),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTimezoneDropdown() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text("Timezone", style: TextStyle(color: AppColors.textSecondary, fontSize: 11.5, fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: AppColors.inputBackground,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.border),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _selectedTz,
              isExpanded: true,
              dropdownColor: AppColors.card,
              style: const TextStyle(
                fontFamily: AppTypography.fontFamilyMono,
                fontSize: 12.5,
                color: AppColors.textMain,
              ),
              items: const [
                DropdownMenuItem(value: "+05:30", child: Text("IST (+05:30)")),
                DropdownMenuItem(value: "+00:00", child: Text("UTC (+00:00)")),
                DropdownMenuItem(value: "-04:00", child: Text("EDT (-04:00)")),
                DropdownMenuItem(value: "-07:00", child: Text("PDT (-07:00)")),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _selectedTz = val);
              },
            ),
          ),
        ),
      ],
    );
  }
}
