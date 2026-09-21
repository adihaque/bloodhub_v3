import 'package:dio/dio.dart';
import '../storage/token_storage.dart';

class ApiClient {
  ApiClient({TokenStorage? storage, String? baseUrl}) : _storage = storage ?? TokenStorage() {
    _dio = Dio(BaseOptions(baseUrl: baseUrl ?? const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000/api/v1'), connectTimeout: const Duration(seconds: 15), receiveTimeout: const Duration(seconds: 20), headers: {'Content-Type': 'application/json'}));
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async { final token = await _storage.accessToken; if (token != null) options.headers['Authorization'] = 'Bearer $token'; handler.next(options); }, onError: (error, handler) async { if (error.response?.statusCode == 401 && !error.requestOptions.path.contains('/auth/refresh')) { final refresh = await _storage.refreshToken; if (refresh != null) { try { final response = await _dio.post('/auth/refresh', data: {'refresh_token': refresh}); final access = response.data['access_token'] as String; await _storage.save(accessToken: access, refreshToken: response.data['refresh_token'] as String?); final retry = await _dio.fetch(error.requestOptions..headers['Authorization'] = 'Bearer $access'); return handler.resolve(retry); } catch (_) { await _storage.clear(); } } } handler.next(error); }));
  }
  late final Dio _dio;
  final TokenStorage _storage;
  Future<Response<dynamic>> get(String path, {Map<String, dynamic>? query}) => _dio.get(path, queryParameters: query);
  Future<Response<dynamic>> post(String path, {Object? data}) => _dio.post(path, data: data);
  Future<Response<dynamic>> put(String path, {Object? data}) => _dio.put(path, data: data);
}
