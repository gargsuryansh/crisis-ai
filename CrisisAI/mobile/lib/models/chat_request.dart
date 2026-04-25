// Day 2 — Saanvi
// Matches shared/contracts/chat_request.json (Section 3 of master guide)
// DO NOT change field names — backend depends on exact snake_case keys.

enum ChatMode {
  online,
  offline,
}

enum ConversationState {
  intake,
  triage,
  immediateAction,
  monitoring,
  escalation,
  postCrisis,
}

class ChatLocation {
  final double? lat;
  final double? lng;

  const ChatLocation({
    required this.lat,
    required this.lng,
  });

  Map<String, dynamic> toJson() {
    return {
      'lat': lat,
      'lng': lng,
    };
  }
}

class ChatRequest {
  final String sessionId;
  final String query;
  final ChatMode mode;
  final ChatLocation location;
  final ConversationState conversationState;
  final String? languageHint;

  const ChatRequest({
    required this.sessionId,
    required this.query,
    required this.mode,
    required this.location,
    required this.conversationState,
    required this.languageHint,
  });

  Map<String, dynamic> toJson() {
    return {
      'session_id': sessionId,
      'query': query,
      'mode': _modeToString(mode),
      'location': location.toJson(),
      'conversation_state': _stateToString(conversationState),
      'language_hint': languageHint,
    };
  }

  String _modeToString(ChatMode mode) {
    switch (mode) {
      case ChatMode.online:
        return 'online';
      case ChatMode.offline:
        return 'offline';
    }
  }

  String _stateToString(ConversationState state) {
    switch (state) {
      case ConversationState.intake:
        return 'INTAKE';
      case ConversationState.triage:
        return 'TRIAGE';
      case ConversationState.immediateAction:
        return 'IMMEDIATE_ACTION';
      case ConversationState.monitoring:
        return 'MONITORING';
      case ConversationState.escalation:
        return 'ESCALATION';
      case ConversationState.postCrisis:
        return 'POST_CRISIS';
    }
  }
}
