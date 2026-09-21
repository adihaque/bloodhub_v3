import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'core/notifications/notification_service.dart';
import 'features/auth/auth_screen.dart';
Future<void> main() async { WidgetsFlutterBinding.ensureInitialized(); try { await Firebase.initializeApp(); } catch (_) {} await NotificationService().initialize(); runApp(const BloodHubApp()); }
class BloodHubApp extends StatelessWidget { const BloodHubApp({super.key}); @override Widget build(BuildContext context) => MaterialApp(title: 'Blood Hub', theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.red), useMaterial3: true), home: const AuthScreen()); }
