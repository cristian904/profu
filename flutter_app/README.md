# Profu Flutter App

Flutter landing page for the Profu application.

## Setup

1. Make sure you have Flutter installed:
```bash
flutter --version
```

2. Install dependencies:
```bash
flutter pub get
```

3. Update the API URL in `lib/main.dart` if your backend is running on a different host/port:
```dart
final String _apiUrl = 'http://localhost:8000/index';
```

For Android emulator, use `http://10.0.2.2:8000/index` instead of `localhost`.

4. Run the app:
```bash
flutter run
```

## Notes

- The app will attempt to connect to the FastAPI backend at `http://localhost:8000/index`
- Make sure the backend is running before launching the Flutter app
- For Android emulator, replace `localhost` with `10.0.2.2`
- For iOS simulator, `localhost` should work
- For physical devices, use your computer's local IP address (e.g., `http://192.168.1.100:8000/index`)
