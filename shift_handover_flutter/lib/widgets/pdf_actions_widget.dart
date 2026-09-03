import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../constants/theme_constants.dart';
import '../services/api_service.dart';

class PdfActionsWidget extends StatelessWidget {
  final String? pdfRelativeUrl;
  final String? pdfFilename;
  final String shiftWindowLabel;

  const PdfActionsWidget({
    Key? key,
    required this.pdfRelativeUrl,
    required this.pdfFilename,
    required this.shiftWindowLabel,
  }) : super(key: key);

  Future<void> _openPdf(BuildContext context, bool download) async {
    final fullUrl = ApiService.getPdfUrl(pdfRelativeUrl);
    if (fullUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("No PDF report generated yet.")),
      );
      return;
    }

    final uri = Uri.parse(fullUrl);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (context.mounted) {
        _showPdfDialog(context, fullUrl);
      }
    }
  }

  void _showPdfDialog(BuildContext context, String fullUrl) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.card,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.border),
        ),
        title: const Row(
          children: [
            Icon(Icons.picture_as_pdf, color: AppColors.blockers, size: 20),
            SizedBox(width: 8),
            Text("PDF Handover Report", style: TextStyle(color: AppColors.textMain, fontSize: 16)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Generated File: ${pdfFilename ?? 'handover_note.pdf'}", style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            const SizedBox(height: 8),
            Text("Shift: $shiftWindowLabel", style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.inputBackground,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.border),
              ),
              child: SelectableText(
                fullUrl,
                style: const TextStyle(
                  fontFamily: AppTypography.fontFamilyMono,
                  fontSize: 11.5,
                  color: AppColors.primaryAccent,
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Close", style: TextStyle(color: AppColors.textSecondary)),
          ),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primaryAccent,
              foregroundColor: const Color(0xFF04140D),
            ),
            onPressed: () async {
              final uri = Uri.parse(fullUrl);
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            },
            icon: const Icon(Icons.open_in_new, size: 16),
            label: const Text("Open in Browser"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        OutlinedButton.icon(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.textMain,
            backgroundColor: AppColors.secondaryBackground,
            side: const BorderSide(color: AppColors.border),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          onPressed: () => _openPdf(context, false),
          icon: const Icon(Icons.visibility_outlined, size: 16, color: AppColors.primaryAccent),
          label: const Text("VIEW PDF", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
        ),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primaryAccent,
            foregroundColor: const Color(0xFF04140D),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          onPressed: () => _openPdf(context, true),
          icon: const Icon(Icons.download, size: 16),
          label: const Text("DOWNLOAD PDF", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
        ),
      ],
    );
  }
}
