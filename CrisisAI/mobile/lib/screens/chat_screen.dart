// Day 3 — Saanvi
// Chat screen with online streaming + offline protocol retrieval
// Supports: API streaming (online) and weighted keyword RAG (offline)
// Matches POST /api/v1/chat/stream contract (Section 3)

import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/chat_request.dart';
import '../services/connectivity_service.dart';
import '../services/offline_rag_service.dart';
import '../services/gemini_nano_service.dart';
import '../services/mediapipe_service.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final String? crisisType;
  final String? severity;
  final List<String> emergencyNumbers;

  const ChatMessage({
    required this.text,
    required this.isUser,
    this.crisisType,
    this.severity,
    this.emergencyNumbers = const [],
  });
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ApiClient _apiClient = ApiClient();
  final TextEditingController _queryController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;
  String _currentStreamingText = '';

  final ConnectivityService _connectivityService = ConnectivityService();
  final OfflineRagService _offlineRagService = OfflineRagService();
  final GeminiNanoService _geminiNanoService = GeminiNanoService();
  final MediaPipeService _mediaPipeService = MediaPipeService();

  bool _isOffline = false;
  String _offlineMessage = '';
  StreamSubscription<bool>? _connectivitySubscription;
  late final Future<void> _protocolsReady;

  @override
  void initState() {
    super.initState();
    _protocolsReady = _offlineRagService.loadProtocols();
    _initializeConnectivity();
    _connectivitySubscription =
        _connectivityService.connectionStream().listen((online) {
      if (!mounted) return;
      setState(() {
        _isOffline = !online;
        _offlineMessage = _isOffline
            ? "You are offline. Using local emergency protocols from device."
            : "";
      });
    });
  }

  Future<void> _initializeConnectivity() async {
    final online = await _connectivityService.isOnline();
    if (!mounted) return;
    setState(() {
      _isOffline = !online;
      _offlineMessage = _isOffline
          ? "You are offline. Using local emergency protocols from device."
          : "";
    });
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    _queryController.dispose();
    _scrollController.dispose();
    _apiClient.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _sendMessage() async {
    final text = _queryController.text.trim();
    if (text.isEmpty) return;

    _queryController.clear();
    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true));
      _isLoading = true;
      _currentStreamingText = '';
    });

    Future.delayed(const Duration(milliseconds: 50), _scrollToBottom);

    final request = ChatRequest(
      sessionId: 'test_session_${DateTime.now().millisecondsSinceEpoch}',
      query: text,
      mode: ChatMode.online,
      location: const ChatLocation(lat: null, lng: null),
      conversationState: ConversationState.intake,
      languageHint: null,
    );

    final bool isOnline = await _connectivityService.isOnline();

    if (isOnline) {
      try {
        // Priority 1: Online Streaming
        await for (final chunk in _apiClient.streamChat(request)) {
          setState(() {
            _currentStreamingText += chunk;
          });
          _scrollToBottom();
        }

        setState(() {
          _messages.add(ChatMessage(
            text: _currentStreamingText,
            isUser: false,
          ));
          _currentStreamingText = '';
          _isLoading = false;
        });
        _scrollToBottom();
      } catch (_) {
        try {
          // Fallback to non-stream chat if streaming fails
          final response = await _apiClient.sendChat(request);
          setState(() {
            _messages.add(ChatMessage(
              text: response.response,
              isUser: false,
              crisisType: response.crisisType,
              severity: response.severity,
              emergencyNumbers: response.emergencyNumbers,
            ));
            _isLoading = false;
          });
          _scrollToBottom();
        } catch (_) {
          // Both online methods failed, switch to offline
          setState(() {
            _messages.add(const ChatMessage(
              text:
                  'Backend unavailable. Switching to offline emergency protocols...',
              isUser: false,
            ));
          });
          await _handleOfflineResponse(text);
        }
      }
    } else {
      await _handleOfflineResponse(text);
    }
    _scrollToBottom();
  }

  Future<void> _handleOfflineResponse(String query) async {
    await _protocolsReady;

    final protocol = _offlineRagService.getBestProtocol(query);
    final rawProtocolText = _offlineRagService.buildOfflineResponse(protocol);
    final numbers =
        _offlineRagService.extractEmergencyNumbers(protocol['emergency_numbers']);

    String? responseText;

    // Priority 2: Gemini Nano (AICore)
    if (await _geminiNanoService.isAvailable()) {
      try {
        final prompt = _mediaPipeService.buildPrompt(query, rawProtocolText);
        responseText = await _geminiNanoService.generate(prompt);
      } catch (_) {
        // Fall through
      }
    }

    // Priority 3: MediaPipe (Gemma)
    if (responseText == null && await _mediaPipeService.isAvailable()) {
      try {
        final prompt = _mediaPipeService.buildPrompt(query, rawProtocolText);
        responseText = await _mediaPipeService.generate(prompt);
      } catch (_) {
        // Fall through
      }
    }

    // Priority 4: Raw RAG Protocol
    responseText ??= rawProtocolText;

    setState(() {
      _messages.add(ChatMessage(
        text: responseText!,
        isUser: false,
        crisisType: protocol['crisis_type']?.toString(),
        severity: protocol['severity']?.toString(),
        emergencyNumbers: numbers,
      ));
      _isLoading = false;
    });
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return Colors.red;
      case 'HIGH':
        return Colors.orange;
      case 'MEDIUM':
        return Colors.amber;
      case 'LOW':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  Widget _buildMessageBubble(ChatMessage message) {
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: message.isUser ? Colors.blue.shade100 : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(16).copyWith(
            bottomRight: message.isUser ? const Radius.circular(0) : null,
            bottomLeft: !message.isUser ? const Radius.circular(0) : null,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (message.severity != null && !message.isUser)
              Container(
                margin: const EdgeInsets.only(bottom: 4),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _getSeverityColor(message.severity!),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  message.severity!.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            Text(
              message.text,
              style: const TextStyle(fontSize: 16),
            ),
            if (message.crisisType != null && !message.isUser)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Chip(
                  label: Text(
                    message.crisisType!,
                    style: const TextStyle(fontSize: 12),
                  ),
                  backgroundColor: Colors.grey.shade300,
                  visualDensity: VisualDensity.compact,
                ),
              ),
            if (message.emergencyNumbers.isNotEmpty && !message.isUser)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Wrap(
                  spacing: 8,
                  children: message.emergencyNumbers.map((number) {
                    return ElevatedButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.phone, size: 16),
                      label: Text(number),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red.shade100,
                        foregroundColor: Colors.red.shade900,
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                      ),
                    );
                  }).toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildStreamingBubble() {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(16).copyWith(
            bottomLeft: const Radius.circular(0),
          ),
        ),
        child: Text(
          '$_currentStreamingText▌',
          style: const TextStyle(fontSize: 16),
        ),
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.all(16.0),
        child: CircularProgressIndicator(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('CrisisAI Emergency Chat'),
        backgroundColor: Colors.red.shade700,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          if (_isOffline)
            Container(
              width: double.infinity,
              color: Colors.deepOrange,
              padding: const EdgeInsets.all(10),
              child: Text(
                _offlineMessage.isNotEmpty
                    ? _offlineMessage
                    : "OFFLINE MODE — Using local protocols",
                style: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
            ),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              itemCount: _messages.length + (_isLoading ? 1 : 0),
              itemBuilder: (context, index) {
                if (index < _messages.length) {
                  return _buildMessageBubble(_messages[index]);
                }
                if (_currentStreamingText.isNotEmpty) {
                  return _buildStreamingBubble();
                }
                return _buildTypingIndicator();
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(8),
            color: Colors.grey.shade100,
            child: SafeArea(
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _queryController,
                      decoration: InputDecoration(
                        hintText: 'Describe your emergency...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                      ),
                      maxLines: 3,
                      minLines: 1,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _sendMessage(),
                      enabled: !_isLoading,
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (_isLoading)
                    const Padding(
                      padding: EdgeInsets.all(12.0),
                      child: SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  else
                    IconButton(
                      icon: const Icon(Icons.send),
                      color: Colors.red,
                      onPressed: _sendMessage,
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
