// Day 2 — Saanvi
// Matches shared/contracts/chat_response.json (Section 3 of master guide)
// DO NOT change JSON field names — backend depends on exact snake_case keys.

class ChatResponse {
  final String sessionId;
  final String response;
  final String crisisType;
  final String severity;
  final List<String> emergencyNumbers;
  final List<String> sources;
  final double confidence;
  final String nextState;
  final bool stream;

  const ChatResponse({
    required this.sessionId,
    required this.response,
    required this.crisisType,
    required this.severity,
    required this.emergencyNumbers,
    required this.sources,
    required this.confidence,
    required this.nextState,
    required this.stream,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      sessionId: json['session_id'] as String,
      response: json['response'] as String,
      crisisType: json['crisis_type'] as String,
      severity: json['severity'] as String,
      emergencyNumbers: (json['emergency_numbers'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          <String>[],
      sources: (json['sources'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          <String>[],
      confidence: json['confidence'] != null
          ? (json['confidence'] as num).toDouble()
          : 0.0,
      nextState: json['next_state'] as String,
      stream: json['stream'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'session_id': sessionId,
      'response': response,
      'crisis_type': crisisType,
      'severity': severity,
      'emergency_numbers': emergencyNumbers,
      'sources': sources,
      'confidence': confidence,
      'next_state': nextState,
      'stream': stream,
    };
  }
}
