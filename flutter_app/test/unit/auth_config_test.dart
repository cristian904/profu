import "package:flutter_test/flutter_test.dart";
import "package:profu_app/auth_config.dart";

void main() {
  test("googleWebClientId is a non-empty string", () {
    expect(googleWebClientId, isNotEmpty);
    expect(googleWebClientId, contains("apps.googleusercontent.com"));
  });
}
