class HandoverItem {
  final String recordId;
  final String source;
  final String summary;
  final String status;
  final String? initialStatus;
  final String? priority;
  final String? assignee;
  final String? details;
  final String timestamp;
  final List<String> progression;
  final String section;

  HandoverItem({
    required this.recordId,
    required this.source,
    required this.summary,
    required this.status,
    this.initialStatus,
    this.priority,
    this.assignee,
    this.details,
    required this.timestamp,
    required this.progression,
    required this.section,
  });

  factory HandoverItem.fromJson(Map<String, dynamic> json, {String defaultSection = "COMPLETED"}) {
    List<String> prog = [];
    if (json['progression'] is List) {
      prog = (json['progression'] as List).map((e) => e.toString()).toList();
    }

    return HandoverItem(
      recordId: json['record_id']?.toString() ?? 'N/A',
      source: json['source']?.toString() ?? 'Unknown System',
      summary: json['summary']?.toString() ?? json['title']?.toString() ?? 'Untitled Activity',
      status: json['status']?.toString() ?? 'unknown',
      initialStatus: json['initial_status']?.toString(),
      priority: json['priority']?.toString() ?? json['severity']?.toString(),
      assignee: json['assignee']?.toString() ?? json['service']?.toString(),
      details: json['details']?.toString() ?? json['notes']?.toString(),
      timestamp: json['timestamp']?.toString() ?? json['timestamp_display'] ?? json['normalized_timestamp'] ?? 'N/A',
      progression: prog,
      section: json['section']?.toString() ?? defaultSection,
    );
  }
}

class ShiftMetrics {
  final int totalRawEvents;
  final int totalCollapsedItems;
  final int completed;
  final int inProgress;
  final int blockers;
  final int watchList;

  ShiftMetrics({
    required this.totalRawEvents,
    required this.totalCollapsedItems,
    required this.completed,
    required this.inProgress,
    required this.blockers,
    required this.watchList,
  });

  factory ShiftMetrics.fromJson(Map<String, dynamic> json) {
    return ShiftMetrics(
      totalRawEvents: (json['total_raw_events'] as num?)?.toInt() ?? 0,
      totalCollapsedItems: (json['total_collapsed_items'] as num?)?.toInt() ?? 0,
      completed: (json['completed'] as num?)?.toInt() ?? 0,
      inProgress: (json['in_progress'] as num?)?.toInt() ?? 0,
      blockers: (json['blockers'] as num?)?.toInt() ?? 0,
      watchList: (json['watch_list'] as num?)?.toInt() ?? 0,
    );
  }
}

class ShiftWindow {
  final String start;
  final String end;
  final String? startUtc;
  final String? endUtc;

  ShiftWindow({
    required this.start,
    required this.end,
    this.startUtc,
    this.endUtc,
  });

  factory ShiftWindow.fromJson(Map<String, dynamic> json) {
    return ShiftWindow(
      start: json['start']?.toString() ?? '',
      end: json['end']?.toString() ?? '',
      startUtc: json['start_utc']?.toString(),
      endUtc: json['end_utc']?.toString(),
    );
  }
}

class HandoverResponse {
  final bool success;
  final String message;
  final String? pdfUrl;
  final String? pdfFilename;
  final ShiftMetrics metrics;
  final ShiftWindow shiftWindow;
  final List<HandoverItem> completed;
  final List<HandoverItem> inProgress;
  final List<HandoverItem> blockers;
  final List<HandoverItem> watchList;

  HandoverResponse({
    required this.success,
    required this.message,
    this.pdfUrl,
    this.pdfFilename,
    required this.metrics,
    required this.shiftWindow,
    required this.completed,
    required this.inProgress,
    required this.blockers,
    required this.watchList,
  });

  factory HandoverResponse.fromJson(Map<String, dynamic> json) {
    final sections = json['sections'] as Map<String, dynamic>? ?? {};

    final compList = (sections['completed'] as List<dynamic>? ?? [])
        .map((e) => HandoverItem.fromJson(e as Map<String, dynamic>, defaultSection: "COMPLETED"))
        .toList();

    final inProgList = (sections['in_progress'] as List<dynamic>? ?? [])
        .map((e) => HandoverItem.fromJson(e as Map<String, dynamic>, defaultSection: "IN PROGRESS"))
        .toList();

    final blockList = (sections['blockers'] as List<dynamic>? ?? [])
        .map((e) => HandoverItem.fromJson(e as Map<String, dynamic>, defaultSection: "BLOCKERS / ESCALATIONS"))
        .toList();

    final watchList = (sections['watch_list'] as List<dynamic>? ?? [])
        .map((e) => HandoverItem.fromJson(e as Map<String, dynamic>, defaultSection: "WATCH-LIST"))
        .toList();

    return HandoverResponse(
      success: json['success'] == true,
      message: json['message']?.toString() ?? '',
      pdfUrl: json['pdf_url']?.toString(),
      pdfFilename: json['pdf_filename']?.toString(),
      metrics: ShiftMetrics.fromJson(json['metrics'] as Map<String, dynamic>? ?? {}),
      shiftWindow: ShiftWindow.fromJson(json['shift_window'] as Map<String, dynamic>? ?? {}),
      completed: compList,
      inProgress: inProgList,
      blockers: blockList,
      watchList: watchList,
    );
  }

  List<HandoverItem> getAllItems() {
    return [...completed, ...inProgress, ...blockers, ...watchList];
  }
}

class SourceStatus {
  final String name;
  final String path;
  final bool connected;
  final String status;
  final int totalRecords;

  SourceStatus({
    required this.name,
    required this.path,
    required this.connected,
    required this.status,
    required this.totalRecords,
  });

  factory SourceStatus.fromJson(Map<String, dynamic> json) {
    return SourceStatus(
      name: json['name']?.toString() ?? 'Source',
      path: json['path']?.toString() ?? '',
      connected: json['connected'] == true,
      status: json['status']?.toString() ?? 'Unknown',
      totalRecords: (json['total_records'] as num?)?.toInt() ?? 0,
    );
  }
}
