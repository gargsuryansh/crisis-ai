// Day 3 — Saanvi
// MediaPipeService - On-device LLM fallback using MediaPipe + Gemma 3 1B
// STUB IMPLEMENTATION: Will return false on emulator (correct behavior).
// Real implementation requires physical Android 12+ device with downloaded Gemma model.
// Master Guide Section 5.3: Priority 3 in offline waterfall.
// Uses OfflineRAGService for retrieval cont
import 'dart:async';
import 'package:flutter/services.dart';

class MediaPipeService {
  static const MethodChannel _channel = MethodChannel('crisisai/mediapipe_llm');

  // Check if MediaPipe LLM inference is available on the device.
  // Returns false on emulators.
  // Returns false if Gemma 3 1B model file is not downloaded.
  // Returns true only on physical Android 12+ with model file present.
  Future<bool> isAvailable() async {
    try {
      final bool? result = await _channel.invokeMethod<bool>('isAvailable');
      return result ?? false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    } catch (_) {
      return false;
    }
  }

  // Generate response using MediaPipe Gemma 3 1B.
  // The prompt should include RAG context from OfflineRagService.
  // Throws StateError if MediaPipe is not available.
  Future<String> generate(String prompt) async {
    final available = await isAvailable();
    if (!available) {
      throw StateError('MediaPipe LLM is not available on this device.');
    }
    try {
      final String? result = await _channel.invokeMethod<String>(
        'generate',
        {'prompt': prompt},
      );
      if (result == null) {
        throw StateError('MediaPipe LLM returned null response.');
      }
      return result;
    } on PlatformException catch (e) {
      throw StateError('MediaPipe LLM generation failed: ${e.message}');
    } on MissingPluginException {
      throw StateError('MediaPipe LLM native bridge not implemented yet.');
    }
  }

  // Build a prompt that includes RAG context for better generation.
  // This method is used to combine retrieved protocol data with user query.
  String buildPrompt(String query, String ragContext) {
    return '''You are an Indian emergency response AI assistant.
Use the following emergency protocol as context to answer the user's question.
Be concise, clear, and action-oriented. Include emergency numbers.

PROTOCOL CONTEXT:
$ragContext

USER QUERY: $query

RESPONSE:''';
  }
}
