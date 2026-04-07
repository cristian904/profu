import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:profu_app/widgets/latex_markdown_body.dart";
import "package:profu_app/widgets/simulari_similar_problems_sheet_body.dart";

void main() {
  testWidgets("sheet shows title, LaTeX body, and action buttons", (WidgetTester tester) async {
    bool opened = false;
    bool closed = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SimulariSimilarProblemsSheetBody(
            message: "Intro\n\n1. Text with \$a+b\$ inline",
            maxBodyHeight: 200,
            onOpenInSolve: () {
              opened = true;
            },
            onClose: () {
              closed = true;
            },
          ),
        ),
      ),
    );

    expect(find.text("Probleme similare"), findsOneWidget);
    expect(find.byType(LatexMarkdownBody), findsOneWidget);
    expect(find.text("Deschide în Rezolvare problemă"), findsOneWidget);
    expect(find.text("Închide"), findsOneWidget);

    await tester.tap(find.text("Deschide în Rezolvare problemă"));
    expect(opened, true);
    expect(closed, false);

    await tester.tap(find.text("Închide"));
    expect(closed, true);
  });

  testWidgets("LatexMarkdownBody receives full message for rendering", (WidgetTester tester) async {
    const String msg = r"$$\int_0^1 x$$";

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SimulariSimilarProblemsSheetBody(
            message: msg,
            maxBodyHeight: 120,
            onOpenInSolve: () {},
            onClose: () {},
          ),
        ),
      ),
    );

    final LatexMarkdownBody body = tester.widget<LatexMarkdownBody>(
      find.byType(LatexMarkdownBody),
    );
    expect(body.data, msg);
  });
}
