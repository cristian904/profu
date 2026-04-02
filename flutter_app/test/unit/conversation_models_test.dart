import "package:flutter_test/flutter_test.dart";
import "package:profu_app/models/conversation_models.dart";

void main() {
  group("ConversationTypeDb", () {
    test("dbValue maps enums", () {
      expect(ConversationType.clarify.dbValue, "clarify");
      expect(ConversationType.clarifySteps.dbValue, "clarify_steps");
      expect(ConversationType.problemSolving.dbValue, "problem_solving");
    });

    test("fromDb parses known values", () {
      expect(ConversationTypeDb.fromDb("clarify"), ConversationType.clarify);
      expect(ConversationTypeDb.fromDb("clarify_steps"), ConversationType.clarifySteps);
      expect(ConversationTypeDb.fromDb("problem_solving"), ConversationType.problemSolving);
    });

    test("fromDb defaults unknown to clarify", () {
      expect(ConversationTypeDb.fromDb("unknown"), ConversationType.clarify);
    });
  });

  group("Conversation", () {
    test("fromJson and toJson round-trip core fields", () {
      final Map<String, dynamic> json = <String, dynamic>{
        "id": 7,
        "user_id": "u1",
        "name": "N",
        "title": "T",
        "school_subject": "Math",
        "type": "clarify",
        "created_at": "2024-06-01T12:00:00.000Z",
      };
      final Conversation c = Conversation.fromJson(json);
      expect(c.id, 7);
      expect(c.userId, "u1");
      expect(c.name, "N");
      expect(c.title, "T");
      expect(c.schoolSubject, "Math");
      expect(c.type, ConversationType.clarify);
      expect(c.toJson()["type"], "clarify");
    });

    test("copyWith updates fields", () {
      final Conversation c = Conversation(
        id: 1,
        userId: "u",
        type: ConversationType.clarify,
        createdAt: DateTime.utc(2024),
      );
      final Conversation n = c.copyWith(name: "X");
      expect(n.name, "X");
      expect(n.id, c.id);
    });
  });

  group("ConversationMessage", () {
    test("fromJson maps fields", () {
      final ConversationMessage m = ConversationMessage.fromJson(<String, dynamic>{
        "id": 3,
        "conversation_id": 9,
        "speaker": "user",
        "content": "hi",
        "created_at": "2024-06-01T12:00:00.000Z",
      });
      expect(m.id, 3);
      expect(m.conversationId, 9);
      expect(m.speaker, "user");
      expect(m.content, "hi");
    });
  });
}
