import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../api/api_client.dart';

typedef QueuedOperation = Future<void> Function(ApiClient client);
class OfflineQueue {
  OfflineQueue(this.client) { _subscription = Connectivity().onConnectivityChanged.listen((_) => flush()); }
  final ApiClient client; final List<QueuedOperation> _pending = []; late final StreamSubscription _subscription;
  void enqueue(QueuedOperation operation) { _pending.add(operation); }
  Future<void> flush() async { while (_pending.isNotEmpty) { try { await _pending.first(client); _pending.removeAt(0); } catch (_) { break; } } }
  Future<void> dispose() => _subscription.cancel();
}
