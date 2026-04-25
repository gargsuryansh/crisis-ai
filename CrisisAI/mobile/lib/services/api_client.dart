// Day 2 — Saanvi
// API client for CrisisAI mobile app
// Uses manual HTTP chunked streaming for /api/v1/chat/stream
// NEVER change baseUrl to localhost for Android emulator.

import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

import '../models/chat_request.dart';
import '../models/chat_response.dart';

class ApiClient {
  final http.Client _client;
  final String baseUrl;

  ApiClient({
    http.Client? client,
    this.baseUrl = 'http://10.0.2.2:8000/api/v1',
  }) : _client = client ?? http.Client();

  Future<ChatResponse> sendChat(ChatRequest request) async {
    final uri = Uri.parse('$baseUrl/chat');
    final response = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(request.toJson()),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to send chat. Status: ${response.statusCode}, Body: ${response.body}');
    }

    return ChatResponse.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Stream<String> streamChat(ChatRequest request) async* {
    final uri = Uri.parse('$baseUrl/chat/stream');
    final httpRequest = http.Request('POST', uri)
      ..headers['Content-Type'] = 'application/json'
      ..headers['Accept'] = 'text/event-stream'
      ..body = jsonEncode(request.toJson());

    final response = await _client.send(httpRequest);

    if (response.statusCode != 200) {
      final body = await response.stream.bytesToString();
      throw Exception('Failed to stream chat. Status: ${response.statusCode}, Body: $body');
    }

    String buffer = '';

    await for (final chunk in response.stream.transform(utf8.decoder)) {
      buffer += chunk;
      int lineEndIndex;

      while ((lineEndIndex = buffer.indexOf('\n')) != -1) {
        final line = buffer.substring(0, lineEndIndex);
        buffer = buffer.substring(lineEndIndex + 1);

        if (line.isEmpty) {
          continue;
        }

        if (line.startsWith('data: ')) {
          final payload = line.substring(6);

          if (payload.trim() == '[DONE]') {
            return;
          }

          try {
            final data = jsonDecode(payload);
            if (data is Map<String, dynamic> && data.containsKey('chunk')) {
              yield data['chunk'] as String;
            }
          } catch (_) {
            // skip malformed JSON safely
          }
        }
      }
    }

    if (buffer.isNotEmpty && buffer.startsWith('data: ')) {
      final payload = buffer.substring(6);
      if (payload.trim() != '[DONE]') {
        try {
          final data = jsonDecode(payload);
          if (data is Map<String, dynamic> && data.containsKey('chunk')) {
            yield data['chunk'] as String;
          }
        } catch (_) {
          // skip
        }
      }
    }
  }

  void dispose() {
    _client.close();
  }
}
