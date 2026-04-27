// Day 4 — Saanvi
// Real FirestoreService using cloud_firestore package.
// Listens to notifications/{firebase_uid} for authority response.

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class FirestoreService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  Stream<String?> listenForResponse(String? uid) {
    if (uid == null) return Stream.value(null);

    return _firestore
        .collection('notifications')
        .doc(uid)
        .snapshots()
        .map((snapshot) {
      if (snapshot.exists && snapshot.data() != null) {
        final data = snapshot.data()!;
        if (data['status'] == 'responded') {
          return data['authority_note'] as String? ?? 'Help is on the way!';
        }
      }
      return null;
    });
  }

  Future<void> signInAnonymously() async {
    if (_auth.currentUser == null) {
      await _auth.signInAnonymously();
    }
  }
}
