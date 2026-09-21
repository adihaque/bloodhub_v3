import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class NotificationService {
  final _local = FlutterLocalNotificationsPlugin();
  Future<void> initialize() async {
    await _local.initialize(const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher'), iOS: DarwinInitializationSettings()));
    try {
      await FirebaseMessaging.instance.requestPermission(alert: true, badge: true, sound: true);
      FirebaseMessaging.onMessage.listen((message) => show(message.notification?.title ?? 'Blood Hub', message.notification?.body ?? 'New update'));
    } catch (_) { /* Firebase configuration is optional during local development. */ }
  }
  Future<void> show(String title, String body) => _local.show(DateTime.now().millisecondsSinceEpoch ~/ 1000, title, body, const NotificationDetails(android: AndroidNotificationDetails('bloodhub_alerts', 'Blood Hub alerts', importance: Importance.high, priority: Priority.high), iOS: DarwinNotificationDetails()));
}
