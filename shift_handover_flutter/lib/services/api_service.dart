import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../models/handover_models.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class BackendUnavailableException extends ApiException {
  BackendUnavailableException([String msg = "Python backend server is unavailable at the configured URL."])
      : super(msg, statusCode: 503);
}

class InvalidShiftRangeException extends ApiException {
  InvalidShiftRangeException([String msg = "Shift start must be earlier than shift end."])
      : super(msg, statusCode: 400);
}

class PdfGenerationException extends ApiException {
  PdfGenerationException([String msg = "PDF compilation failed on the backend publisher."])
      : super(msg, statusCode: 500);
}

class ApiService {
  // Configurable base URL: easily switchable between localhost, Android emulator, or deployed host
  static String baseUrl = "http://localhost:5050";

  /// Fetches connection health and record counts of data sources.
  static Future<List<SourceStatus>> fetchSourceStatus() async {
    try {
      final uri = Uri.parse("$baseUrl/api/status");
      final response = await http.get(uri).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        final sources = data['sources'] as List<dynamic>? ?? [];
        return sources.map((s) => SourceStatus.fromJson(s as Map<String, dynamic>)).toList();
      } else {
        throw ApiException("Server returned status code ${response.statusCode}", statusCode: response.statusCode);
      }
    } on SocketException catch (_) {
      throw BackendUnavailableException();
    } on http.ClientException catch (_) {
      throw BackendUnavailableException();
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException("Failed to connect to backend: ${e.toString()}");
    }
  }

  /// Triggers shift handover generation on the Python backend.
  static Future<HandoverResponse> generateHandover({
    required String shiftStart,
    required String shiftEnd,
    bool dummy = false,
  }) async {
    try {
      final uri = Uri.parse("$baseUrl/api/generate");
      final body = json.encode({
        "shift_start": shiftStart,
        "shift_end": shiftEnd,
        "dummy": dummy,
      });

      final response = await http.post(
        uri,
        headers: {"Content-Type": "application/json"},
        body: body,
      ).timeout(const Duration(seconds: 15));

      final data = json.decode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200 && data['success'] == true) {
        return HandoverResponse.fromJson(data);
      } else if (response.statusCode == 400) {
        throw InvalidShiftRangeException(data['error']?.toString() ?? "Invalid shift parameters.");
      } else if (response.statusCode == 500) {
        throw PdfGenerationException(data['error']?.toString() ?? "Backend processing error.");
      } else {
        throw ApiException(data['error']?.toString() ?? "Handover generation failed.", statusCode: response.statusCode);
      }
    } on SocketException catch (_) {
      throw BackendUnavailableException();
    } on http.ClientException catch (_) {
      throw BackendUnavailableException();
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException("Error communicating with backend: ${e.toString()}");
    }
  }

  /// Helper to get full PDF download URL.
  static String getPdfUrl(String? relativeUrl) {
    if (relativeUrl == null || relativeUrl.isEmpty) return "";
    if (relativeUrl.startsWith("http://") || relativeUrl.startsWith("https://")) {
      return relativeUrl;
    }
    return "$baseUrl${relativeUrl.startsWith('/') ? '' : '/'}$relativeUrl";
  }
}
