// Day 3 — Saanvi
// GeminiNanoService - On-device Gemini Nano via Android 14+ AICore
// STUB IMPLEMENTATION: Will return false on emulator (correct behavior).
// Real platform-channel implementation will be added when physical Android 14+ device is available.
// Master Guide Section 5.3: Priority 2 in offline waterfall.

import 'dart:async';
import 'package:flutter/services.dart';

class GeminiNanoService {
  static const MethodChannel _channel = MethodChannel('crisisai/gemini_nano');

  // Check if AICore is available on the device.
  // Returns false on emulators always.
  // Returns false on Android 13 and below.
  // Returns true only on Android 14+ with AICore + Gemini Nano enabled.
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

  // Generate response using on-device Gemini Nano.
  // The prompt should already include retrieved RAG context.
  // Throws StateError if AICore is not available (caller must check first).
  Future<String> generate(String prompt) async {
    final available = await isAvailable();
    if (!available) {
      throw StateError('Gemini Nano is not available on this device.');
    }
    try {
      final String? result = await _channel.invokeMethod<String>(
        'generate',
        {'prompt': prompt},
      );
      if (result == null) {
        throw StateError('Gemini Nano returned null response.');
      }
      return result;
    } on PlatformException catch (e) {
      throw StateError('Gemini Nano generation failed: ${e.message}');
    } on MissingPluginException {
      throw StateError('Gemini Nano native bridge not implemented yet.');
    }
  }
}
