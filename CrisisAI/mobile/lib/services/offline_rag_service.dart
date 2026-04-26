// Day 3 — Saanvi
// OfflineRAGService (Approach 4) - Loads emergency_protocols_enhanced.json and performs
// weighted keyword search for offline retrieval. This is the foundation layer.

import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;

class OfflineRagService {
  List<Map<String, dynamic>> _protocols = [];

  Future<void> loadProtocols() async {
    try {
      final String jsonString = await rootBundle
          .loadString('assets/protocols/emergency_protocols_enhanced.json');
      final Map<String, dynamic> jsonData = jsonDecode(jsonString);
      if (jsonData['protocols'] != null && jsonData['protocols'] is List) {
        _protocols = List<Map<String, dynamic>>.from(jsonData['protocols']);
      }
    } catch (e) {
      _protocols = [];
    }
  }

  Set<String> _expandQueryWords(String query) {
    final String lowerQuery = query.toLowerCase();
    final List<String> baseWords =
        lowerQuery.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).toList();
    final Set<String> words = Set<String>.from(baseWords);

    for (final word in baseWords) {
      if (['snake', 'saanp', 'kaat', 'kata', 'das', 'venom', 'zehar']
          .contains(word)) {
        words.addAll(['snake', 'snakebite', 'bite', 'venom', 'poison']);
      }
      if (['fire', 'aag', 'jal', 'burn', 'smoke', 'dhua'].contains(word)) {
        words.addAll(['fire', 'burn', 'smoke', 'evacuation']);
      }
      if (['flood', 'baadh', 'pani', 'water', 'waterlogging'].contains(word)) {
        words.addAll(['flood', 'water', 'drowning', 'evacuation']);
      }
      if (['earthquake', 'bhukamp', 'tremor', 'shaking'].contains(word)) {
        words.addAll(['earthquake', 'collapse', 'building', 'tremor']);
      }
      if ([
        'medical',
        'behosh',
        'unconscious',
        'chest',
        'seene',
        'heart',
        'breathing',
        'cpr'
      ].contains(word)) {
        words.addAll([
          'medical',
          'unconscious',
          'heart',
          'cpr',
          'breathing',
          'ambulance'
        ]);
      }
      if (['accident', 'crash', 'road', 'gaadi', 'car', 'bike']
          .contains(word)) {
        words.addAll(['accident', 'road', 'injury', 'bleeding']);
      }
      if (['chemical', 'gas', 'leak', 'cylinder'].contains(word)) {
        words.addAll(['chemical', 'gas', 'leak', 'poison', 'evacuation']);
      }
      if (['heat', 'garmi', 'loo', 'heatstroke', 'dehydration']
          .contains(word)) {
        words.addAll(['heatstroke', 'heat', 'dehydration', 'water']);
      }
      if (['drown', 'drowning', 'doob', 'dub'].contains(word)) {
        words.addAll(['drowning', 'water', 'rescue']);
      }
    }

    return words;
  }

  Map<String, dynamic> getBestProtocol(String query) {
    if (_protocols.isEmpty) {
      return _getDefaultProtocol();
    }

    final Set<String> words = _expandQueryWords(query);

    if (words.isEmpty) {
      return _getDefaultProtocol();
    }

    Map<String, dynamic>? bestProtocol;
    int maxScore = -1;

    for (final protocol in _protocols) {
      int score = 0;

      final String crisisType =
          (protocol['crisis_type']?.toString() ?? '').toLowerCase();
      final String title = (protocol['title']?.toString() ?? '').toLowerCase();
      final String situation =
          (protocol['situation']?.toString() ?? '').toLowerCase();
      final String content =
          (protocol['content']?.toString() ?? '').toLowerCase();

      final List<dynamic> tagsDynamic = protocol['tags'] ?? [];
      final List<String> tags =
          tagsDynamic.map((e) => e.toString().toLowerCase()).toList();

      final List<dynamic> stepsDynamic = protocol['steps'] ?? [];
      final String stepsText = stepsDynamic
          .map((s) => s['action']?.toString() ?? '')
          .join(' ')
          .toLowerCase();

      final List<dynamic> avoidDynamic = protocol['what_to_avoid'] ?? [];
      final String avoidText = avoidDynamic
          .map((s) => s['action']?.toString() ?? '')
          .join(' ')
          .toLowerCase();

      for (final word in words) {
        if (crisisType.contains(word)) score += 50;
        if (title.contains(word)) score += 25;

        bool tagMatched = false;
        for (final tag in tags) {
          if (tag.contains(word)) {
            tagMatched = true;
            break;
          }
        }
        if (tagMatched) score += 20;

        if (situation.contains(word)) score += 15;
        if (content.contains(word)) score += 10;
        if (stepsText.contains(word)) score += 5;
        if (avoidText.contains(word)) score += 5;
      }

      if (score > maxScore) {
        maxScore = score;
        bestProtocol = protocol;
      } else if (score == maxScore && bestProtocol != null && score > 0) {
        final int currentSeverityWeight =
            _getSeverityWeight(protocol['severity']?.toString() ?? '');
        final int bestSeverityWeight =
            _getSeverityWeight(bestProtocol['severity']?.toString() ?? '');
        if (currentSeverityWeight > bestSeverityWeight) {
          bestProtocol = protocol;
        }
      }
    }

    if (maxScore <= 0 || bestProtocol == null) {
      return _getDefaultProtocol();
    }

    return bestProtocol;
  }

  int _getSeverityWeight(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 4;
      case 'high':
        return 3;
      case 'medium':
        return 2;
      case 'low':
        return 1;
      default:
        return 0;
    }
  }

  List<String> extractSteps(dynamic stepsData) {
    if (stepsData != null && stepsData is List) {
      return stepsData
          .map((e) => e['action']?.toString() ?? '')
          .where((s) => s.isNotEmpty)
          .toList();
    }
    return [];
  }

  List<String> extractAvoidActions(dynamic avoidData) {
    if (avoidData != null && avoidData is List) {
      return avoidData
          .map((e) => e['action']?.toString() ?? '')
          .where((s) => s.isNotEmpty)
          .toList();
    }
    return [];
  }

  List<String> extractEmergencyNumbers(dynamic emergencyData) {
    final Set<String> numbers = {};

    if (emergencyData != null && emergencyData is Map<String, dynamic>) {
      final dynamic primary = emergencyData['primary'];
      if (primary != null && primary is List) {
        for (var item in primary) {
          final number = item['number']?.toString();
          if (number != null && number.isNotEmpty) {
            numbers.add(number);
          }
        }
      }

      final dynamic secondary = emergencyData['secondary'];
      if (secondary != null && secondary is List) {
        for (var item in secondary) {
          final number = item['number']?.toString();
          if (number != null && number.isNotEmpty) {
            numbers.add(number);
          }
        }
      }
    }

    if (numbers.isEmpty) {
      return ['112'];
    }
    return numbers.toList();
  }

  String buildOfflineResponse(Map<String, dynamic> protocol) {
    final StringBuffer buffer = StringBuffer();

    final String title = protocol['title']?.toString() ?? 'Emergency Protocol';
    buffer.writeln(title);
    buffer.writeln();

    final String situation = protocol['situation']?.toString() ?? '';
    if (situation.isNotEmpty) {
      buffer.writeln('Situation: $situation');
      buffer.writeln();
    }

    final List<String> steps = extractSteps(protocol['steps']);
    if (steps.isNotEmpty) {
      buffer.writeln('Steps:');
      for (int i = 0; i < steps.length; i++) {
        buffer.writeln('${i + 1}. ${steps[i]}');
      }
      buffer.writeln();
    }

    final List<String> avoidActions =
        extractAvoidActions(protocol['what_to_avoid']);
    if (avoidActions.isNotEmpty) {
      buffer.writeln('Avoid:');
      for (final action in avoidActions) {
        buffer.writeln('- $action');
      }
      buffer.writeln();
    }

    buffer.write('Call emergency services if danger continues.');
    return buffer.toString();
  }

  Map<String, dynamic> _getDefaultProtocol() {
    return {
      'crisis_type': 'unknown',
      'severity': 'high',
      'title': 'General Emergency Protocol',
      'situation': 'Unknown emergency situation.',
      'steps': [
        {'action': 'Stay calm and assess the situation.'},
        {'action': 'Move to a safe location if possible.'},
        {'action': 'Call emergency services immediately.'}
      ],
      'what_to_avoid': [
        {'action': 'Do not panic.'},
        {'action': 'Do not put yourself in danger.'}
      ],
      'emergency_numbers': {
        'primary': [
          {'number': '112', 'service': 'General Emergency'}
        ]
      }
    };
  }
}
