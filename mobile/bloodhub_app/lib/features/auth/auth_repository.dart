import '../../core/api/api_client.dart';
import '../../core/storage/token_storage.dart';
class AuthRepository {
  AuthRepository(this.api, this.storage); final ApiClient api; final TokenStorage storage;
  Future<Map<String, dynamic>> login(String phone, String password) async => _save(await api.post('/auth/login', data: {'phone': phone, 'password': password}));
  Future<Map<String, dynamic>> register(Map<String, dynamic> data) async => _save(await api.post('/auth/register', data: data));
  Future<Map<String, dynamic>> _save(dynamic response) async { final data = Map<String, dynamic>.from(response.data as Map); await storage.save(accessToken: data['access_token'] as String, refreshToken: data['refresh_token'] as String?); return data; }
  Future<void> logout() => storage.clear();
}
