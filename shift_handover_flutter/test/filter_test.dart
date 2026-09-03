import 'package:flutter_test/flutter_test.dart';
import 'package:shift_handover_flutter/models/handover_models.dart';
import 'package:shift_handover_flutter/widgets/filter_panel.dart';

void main() {
  group('Handover Models & Deduplication Serialization', () {
    test('HandoverItem fromJson parses correctly with progression', () {
      final json = {
        "record_id": "TCK-1001",
        "source": "Ticketing",
        "summary": "Payment API timeout issue resolved",
        "status": "completed",
        "priority": "P1",
        "assignee": "Alex Rivera",
        "timestamp": "2026-09-03T18:45:00+05:30",
        "progression": ["17:10 In Progress", "18:00 In Progress", "18:45 Completed"],
        "section": "COMPLETED",
      };

      final item = HandoverItem.fromJson(json);
      expect(item.recordId, "TCK-1001");
      expect(item.source, "Ticketing");
      expect(item.summary, "Payment API timeout issue resolved");
      expect(item.status, "completed");
      expect(item.progression.length, 3);
      expect(item.section, "COMPLETED");
    });

    test('HandoverResponse fromJson maps all 4 sections', () {
      final responseJson = {
        "success": true,
        "message": "Generated",
        "pdf_url": "/api/download/test.pdf",
        "metrics": {
          "total_raw_events": 14,
          "total_collapsed_items": 9,
          "completed": 3,
          "in_progress": 2,
          "blockers": 2,
          "watch_list": 2
        },
        "shift_window": {
          "start": "2026-09-03T17:00:00+05:30",
          "end": "2026-09-03T20:00:00+05:30",
        },
        "sections": {
          "completed": [
            {"record_id": "TCK-1001", "source": "Ticketing", "summary": "Payment API", "status": "completed"}
          ],
          "in_progress": [
            {"record_id": "TCK-1002", "source": "Ticketing", "summary": "Stripe webhook", "status": "in_progress"}
          ],
          "blockers": [
            {"record_id": "TCK-1003", "source": "Ticketing", "summary": "Replication lag", "status": "blocked"}
          ],
          "watch_list": [
            {"record_id": "TCK-1005", "source": "Ticketing", "summary": "Canary gRPC", "status": "monitoring"}
          ]
        }
      };

      final response = HandoverResponse.fromJson(responseJson);
      expect(response.success, true);
      expect(response.completed.length, 1);
      expect(response.inProgress.length, 1);
      expect(response.blockers.length, 1);
      expect(response.watchList.length, 1);
      expect(response.metrics.completed, 3);
      expect(response.pdfUrl, "/api/download/test.pdf");
    });
  });

  group('FilterCriteria Logic', () {
    test('Filter criteria search matching', () {
      final criteria = FilterCriteria(searchQuery: "payment");
      expect(criteria.isActive, true);

      final item1 = HandoverItem(
        recordId: "TCK-1001",
        source: "Ticketing",
        summary: "Payment API timeout issue resolved",
        status: "completed",
        timestamp: "2026-09-03T18:45:00+05:30",
        progression: [],
        section: "COMPLETED",
      );

      final item2 = HandoverItem(
        recordId: "TCK-1002",
        source: "Ticketing",
        summary: "Stripe webhook migration",
        status: "in_progress",
        timestamp: "2026-09-03T19:10:00+05:30",
        progression: [],
        section: "IN PROGRESS",
      );

      final query = criteria.searchQuery.toLowerCase();
      expect(item1.summary.toLowerCase().contains(query), true);
      expect(item2.summary.toLowerCase().contains(query), false);
    });

    test('Filter criteria source matching', () {
      final criteria = FilterCriteria(source: "Incident");
      expect(criteria.isActive, true);
    });
  });
}
