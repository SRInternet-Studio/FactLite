## 一、 `CustomJudge` 的开发规范（Design Specification）

### 1. 输入规范 (Input Contract)
用户传入的自定义裁判函数（`evalFunc`）必须接受两个参数：
*   `userPrompt` (string): 用户的原始提问。
*   `answer` (string): 大模型生成的初步回答。

> 注意：函数可以是同步函数，也可以是 `async` 异步函数。框架会自动处理两种情况。

### 2. 输出规范 (Output Contract)
这是最重要的一点！为了让框架底层的 `verify` 能够统一处理，自定义函数**必须且只能返回一个包含特定 Key 的对象（Object）**：
```javascript
{
    is_pass: true / false,  // 布尔值，代表是否通过了质检
    feedback: "..."         // 字符串，如果不通过，说明具体原因；如果通过，可为空字符串
}
```

## 二、 示例

比如，我们写一个**"绝对不能包含脏话，且字数不能少于10个字"**的本地校验器（完全不需要调 API）：

```javascript
// test_custom.js
import OpenAI from "openai";
import { verify, rules } from "factlite";

// 1. 开发者自己定义一个普通的 JavaScript 函数
function myStrictCompanyPolicyJudge(prompt, answer) {
  // 规则1：字数太少不行
  if (answer.length < 10) {
    return { is_pass: false, feedback: "Your answer is too short. It must be at least 10 characters long." };
  }

  // 规则2：不能包含竞品的名字
  const bannedWords = ["Apple", "iPhone"];
  for (const word of bannedWords) {
    if (answer.toLowerCase().includes(word.toLowerCase())) {
      return { is_pass: false, feedback: `You are forbidden from mentioning the competitor '${word}'. Change the wording.` };
    }
  }

  // 如果都没问题，放行
  return { is_pass: true, feedback: "" };
}

// 2. 像搭积木一样塞进你的框架
const chat = verify({
  rule: new rules.CustomJudge(myStrictCompanyPolicyJudge),
})(async function (prompt) {
  const client = new OpenAI({ apiKey: "your-key" });
  const response = await client.chat.completions.create({
    model: "gpt-3.5-turbo",
    messages: [{ role: "user", content: prompt }],
  });
  return response.choices[0].message.content;
});

// 试着让他犯错
console.log(await chat("用一句话夸一下我们的手机，可以提到iPhone作为对比。"));
```

## 三、 异步自定义裁判

`CustomJudge` 也支持异步裁判函数，例如需要查数据库或调用外部 API 的场景：

```javascript
async function asyncDatabaseJudge(prompt, answer) {
  // 假设我们需要查数据库来验证答案
  const factExists = await checkFactInDatabase(answer);
  if (!factExists) {
    return { is_pass: false, feedback: "The stated fact could not be verified in our database." };
  }
  return { is_pass: true, feedback: "" };
}

const chat = verify({
  rule: new rules.CustomJudge(asyncDatabaseJudge),
})(async function (prompt) {
  // ... 你的 LLM 调用逻辑
});
