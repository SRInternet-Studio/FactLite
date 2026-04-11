import 'package:flutter_test/flutter_test.dart';
import 'package:factlite/factlite.dart';

void main() {
  group('EvaluationResult', () {
    test('fromMap creates correct result', () {
      final result = EvaluationResult.fromMap({
        'is_pass': true,
        'feedback': '',
      });
      expect(result.isPass, true);
      expect(result.feedback, '');
    });

    test('fromMap handles failed result', () {
      final result = EvaluationResult.fromMap({
        'is_pass': false,
        'feedback': 'Answer is incorrect.',
      });
      expect(result.isPass, false);
      expect(result.feedback, 'Answer is incorrect.');
    });

    test('toMap returns correct map', () {
      const result = EvaluationResult(isPass: true, feedback: 'Good');
      final map = result.toMap();
      expect(map['is_pass'], true);
      expect(map['feedback'], 'Good');
    });
  });

  group('FallbackActions', () {
    test('ReturnBest returns last answer', () async {
      final action = ReturnBest();
      final result = await action.execute(
        prompt: 'test prompt',
        lastAnswer: 'test answer',
        feedback: 'some feedback',
      );
      expect(result, 'test answer');
    });

    test('RaiseError throws exception', () async {
      final action = RaiseError();
      expect(
        () => action.execute(
          prompt: 'test prompt',
          lastAnswer: 'test answer',
          feedback: 'some feedback',
        ),
        throwsA(isA<FactLiteVerificationException>()),
      );
    });

    test('ReturnSafeMessage returns default safe message', () async {
      final action = ReturnSafeMessage();
      final result = await action.execute(
        prompt: 'test prompt',
        lastAnswer: 'test answer',
        feedback: 'some feedback',
      );
      expect(result, '抱歉，AI 暂时无法针对该问题给出有确切把握的回答。');
    });

    test('ReturnSafeMessage returns custom safe message', () async {
      final action = ReturnSafeMessage(
          safeMessage: 'Sorry, I cannot answer that.');
      final result = await action.execute(
        prompt: 'test prompt',
        lastAnswer: 'test answer',
        feedback: 'some feedback',
      );
      expect(result, 'Sorry, I cannot answer that.');
    });
  });

  group('CustomJudge', () {
    test('passes with valid evaluation function', () async {
      final judge = CustomJudge(
        evalFunc: (String userPrompt, String answer) {
          return {'is_pass': true, 'feedback': ''};
        },
      );
      final result = await judge.evaluate('test', 'answer');
      expect(result.isPass, true);
      expect(result.feedback, '');
    });

    test('fails with valid evaluation function', () async {
      final judge = CustomJudge(
        evalFunc: (String userPrompt, String answer) {
          return {'is_pass': false, 'feedback': 'Too short'};
        },
      );
      final result = await judge.evaluate('test', 'hi');
      expect(result.isPass, false);
      expect(result.feedback, 'Too short');
    });

    test('handles async evaluation function', () async {
      final judge = CustomJudge(
        evalFunc: (String userPrompt, String answer) async {
          await Future.delayed(const Duration(milliseconds: 10));
          return {'is_pass': true, 'feedback': ''};
        },
      );
      final result = await judge.evaluate('test', 'answer');
      expect(result.isPass, true);
    });

    test('handles error in evaluation function', () async {
      final judge = CustomJudge(
        evalFunc: (String userPrompt, String answer) {
          throw Exception('Test error');
        },
      );
      final result = await judge.evaluate('test', 'answer');
      expect(result.isPass, false);
      expect(result.feedback, contains('Error in custom judge'));
    });

    test('handles missing is_pass key', () async {
      final judge = CustomJudge(
        evalFunc: (String userPrompt, String answer) {
          return {'feedback': 'missing is_pass'};
        },
      );
      final result = await judge.evaluate('test', 'answer');
      expect(result.isPass, false);
      expect(result.feedback, contains("'is_pass'"));
    });

    test('handles missing feedback key', () async {
      final judge = CustomJudge(
        evalFunc: (String userPrompt, String answer) {
          return {'is_pass': true};
        },
      );
      final result = await judge.evaluate('test', 'answer');
      expect(result.isPass, false);
      expect(result.feedback, contains("'feedback'"));
    });
  });

  group('FactLiteConfig', () {
    test('creates with defaults', () {
      final config = FactLiteConfig(
        rule: CustomJudge(
          evalFunc: (String p, String a) => {'is_pass': true, 'feedback': ''},
        ),
      );
      expect(config.maxRetries, 2);
      expect(config.onFail, isA<ReturnBest>());
    });

    test('creates with custom values', () {
      final config = FactLiteConfig(
        rule: CustomJudge(
          evalFunc: (String p, String a) => {'is_pass': true, 'feedback': ''},
        ),
        maxRetries: 5,
        onFail: RaiseError(),
      );
      expect(config.maxRetries, 5);
      expect(config.onFail, isA<RaiseError>());
    });
  });

  group('verify', () {
    test('returns answer when evaluation passes on first try', () async {
      final result = await verify(
        prompt: 'What is 1+1?',
        generator: (prompt) async => 'The answer is 2.',
        rule: CustomJudge(
          evalFunc: (String userPrompt, String answer) {
            return {'is_pass': true, 'feedback': ''};
          },
        ),
      );
      expect(result, 'The answer is 2.');
    });

    test('retries and corrects on failure', () async {
      int callCount = 0;
      final result = await verify(
        prompt: 'What is 1+1?',
        generator: (prompt) async {
          callCount++;
          if (callCount == 1) {
            return 'The answer is 3.'; // Wrong answer
          }
          return 'The answer is 2.'; // Corrected answer
        },
        rule: CustomJudge(
          evalFunc: (String userPrompt, String answer) {
            if (answer.contains('3')) {
              return {'is_pass': false, 'feedback': '1+1 is not 3'};
            }
            return {'is_pass': true, 'feedback': ''};
          },
        ),
        maxRetries: 2,
      );
      expect(result, 'The answer is 2.');
      expect(callCount, 2);
    });

    test('falls back to ReturnBest after max retries', () async {
      final result = await verify(
        prompt: 'test',
        generator: (prompt) async => 'always wrong',
        rule: CustomJudge(
          evalFunc: (String userPrompt, String answer) {
            return {'is_pass': false, 'feedback': 'Always fails'};
          },
        ),
        maxRetries: 1,
        onFail: ReturnBest(),
      );
      expect(result, 'always wrong');
    });

    test('falls back to ReturnSafeMessage after max retries', () async {
      final result = await verify(
        prompt: 'test',
        generator: (prompt) async => 'always wrong',
        rule: CustomJudge(
          evalFunc: (String userPrompt, String answer) {
            return {'is_pass': false, 'feedback': 'Always fails'};
          },
        ),
        maxRetries: 0,
        onFail: ReturnSafeMessage(safeMessage: 'Cannot answer.'),
      );
      expect(result, 'Cannot answer.');
    });

    test('falls back to RaiseError after max retries', () async {
      expect(
        () => verify(
          prompt: 'test',
          generator: (prompt) async => 'always wrong',
          rule: CustomJudge(
            evalFunc: (String userPrompt, String answer) {
              return {'is_pass': false, 'feedback': 'Always fails'};
            },
          ),
          maxRetries: 0,
          onFail: RaiseError(),
        ),
        throwsA(isA<FactLiteVerificationException>()),
      );
    });

    test('uses config when provided', () async {
      final config = FactLiteConfig(
        rule: CustomJudge(
          evalFunc: (String userPrompt, String answer) {
            return {'is_pass': true, 'feedback': ''};
          },
        ),
        maxRetries: 1,
        onFail: ReturnBest(),
      );

      final result = await verify(
        prompt: 'test',
        generator: (prompt) async => 'answer',
        config: config,
      );
      expect(result, 'answer');
    });

    test('throws when no rule provided', () {
      expect(
        () => verify(
          prompt: 'test',
          generator: (prompt) async => 'answer',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('VerifiedGenerator', () {
    test('wraps generator with verification', () async {
      final verifiedAsk = VerifiedGenerator(
        config: FactLiteConfig(
          rule: CustomJudge(
            evalFunc: (String userPrompt, String answer) {
              return {'is_pass': true, 'feedback': ''};
            },
          ),
        ),
        generator: (prompt) async => 'verified answer',
      );

      final result = await verifiedAsk('test');
      expect(result, 'verified answer');
    });
  });
}
