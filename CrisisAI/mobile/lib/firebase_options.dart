// Day 4 — Saanvi
// Manual Firebase options for Android demo
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError(
        'DefaultFirebaseOptions have not been configured for web - '
        'you can reconfigure this by running the FlutterFire CLI again.',
      );
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not supported for this platform.',
        );
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyB0ONpVsAguKPryWmMIXf61KbJQKlBD5aw',
    appId: '1:402850332580:android:652a3e5e9f795e56de0b31',
    messagingSenderId: '402850332580',
    projectId: 'crisisai-2026',
    storageBucket: 'crisisai-2026.firebasestorage.app',
  );
}
