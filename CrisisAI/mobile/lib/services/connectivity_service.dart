// Day 3 — Saanvi
// ConnectivityService checks network status for offline waterfall logic.

import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';

class ConnectivityService {
  final Connectivity _connectivity = Connectivity();

  bool _isOnlineResult(List<ConnectivityResult> results) {
    return results.contains(ConnectivityResult.mobile) ||
           results.contains(ConnectivityResult.wifi) ||
           results.contains(ConnectivityResult.ethernet);
  }

  Future<bool> isOnline() async {
    final results = await _connectivity.checkConnectivity();
    return _isOnlineResult(results);
  }

  Stream<bool> connectionStream() {
    return _connectivity.onConnectivityChanged.map(_isOnlineResult);
  }
}
