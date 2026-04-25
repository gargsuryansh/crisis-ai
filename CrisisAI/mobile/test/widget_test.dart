// Day 2 — Saanvi
// Basic widget test for CrisisAI Flutter app.
// Updated after replacing the default counter app with CrisisAIApp.

import 'package:flutter_test/flutter_test.dart';
import 'package:crisis_ai/main.dart';

void main() {
  testWidgets('CrisisAI app launches chat screen', (WidgetTester tester) async {
    await tester.pumpWidget(const CrisisAIApp());

    expect(find.text('CrisisAI Emergency Chat'), findsOneWidget);
    expect(find.text('Describe your emergency...'), findsOneWidget);
  });
}
