// Day 2 — Saanvi
// CrisisAI Flutter app entry point
// Launches the emergency chat screen for API streaming integration.

import 'package:flutter/material.dart';
import 'screens/chat_screen.dart';

void main() {
  runApp(const CrisisAIApp());
}

class CrisisAIApp extends StatelessWidget {
  const CrisisAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CrisisAI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.red),
        scaffoldBackgroundColor: Colors.white,
      ),
      home: const ChatScreen(),
    );
  }
}
