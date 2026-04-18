import OpenAI from "openai";
import { verify, rules, actions } from "./index.js";

// Set your OpenAI API key
const apiKey = "your_api_key";

// 配置
const config = verify.config({
  rule: new rules.LLMJudge({
    model: "gpt-4o-mini",
    baseURL: "https://free.v36.cm/v1",
    apiKey: "your_api_key",
  }),
  maxRetries: 2,
  onFail: new actions.ReturnBest(),
});

// 1. 测试基本功能
console.log("=== 测试 1: 基本函数测试 ===");

const askAI = verify({ config })(async function (userPromptStr) {
  const client = new OpenAI({
    apiKey,
    baseURL: "https://api.deepseek.com/v1",
  });
  const response = await client.chat.completions.create({
    model: "deepseek-chat",
    messages: [{ role: "user", content: userPromptStr }],
  });
  return response.choices[0].message.content;
});

// 测试事实错误的问题
const result1 = await askAI("李白是宋朝的皇帝吗？");
console.log("事实错误测试:", result1);

// 测试事实正确的问题
const result2 = await askAI("李白是哪个朝代的诗人？");
console.log("事实正确测试:", result2);

// 2. 测试自定义裁判
console.log("\n=== 测试 2: 自定义裁判测试 ===");

// 定义自定义裁判函数
function myCustomJudge(userPrompt, answer) {
  // 规则1：字数检查
  if (answer.length < 20) {
    return {
      is_pass: false,
      feedback: "Answer is too short. It must be at least 20 characters long.",
    };
  }

  // 规则2：关键词检查
  if (answer.includes("错误")) {
    return {
      is_pass: false,
      feedback: "Answer contains the word 'error'. Please rephrase.",
    };
  }

  // 规则3：必须包含特定关键词
  if (userPrompt.includes("李白") && !answer.includes("李白")) {
    return {
      is_pass: false,
      feedback: "Answer must mention '李白'.",
    };
  }

  return { is_pass: true, feedback: "" };
}

const chatWithCustomJudge = verify({
  rule: new rules.CustomJudge(myCustomJudge),
})(async function (prompt) {
  const client = new OpenAI({
    apiKey,
    baseURL: "https://api.deepseek.com/v1",
  });
  const response = await client.chat.completions.create({
    model: "deepseek-chat",
    messages: [{ role: "user", content: prompt }],
  });
  return response.choices[0].message.content;
});

// 测试字数不足的情况
const customResult1 = await chatWithCustomJudge("用一个字回答：好吗？");
console.log("自定义裁判 - 字数不足测试:", customResult1);

// 测试正常情况
const customResult2 = await chatWithCustomJudge("李白是谁？");
console.log("自定义裁判 - 正常测试:", customResult2);

// 3. 测试错误处理
console.log("\n=== 测试 3: 错误处理测试 ===");

// 定义一个会出错的自定义裁判
function errorJudge(userPrompt, answer) {
  // 故意引发错误
  throw new Error("This is a test error");
}

const chatWithErrorJudge = verify({
  rule: new rules.CustomJudge(errorJudge),
})(async function (prompt) {
  const client = new OpenAI({
    apiKey,
    baseURL: "https://api.deepseek.com/v1",
  });
  const response = await client.chat.completions.create({
    model: "deepseek-chat",
    messages: [{ role: "user", content: prompt }],
  });
  return response.choices[0].message.content;
});

// 测试错误处理
const errorResult = await chatWithErrorJudge("你好吗？");
console.log("错误处理测试:", errorResult);

console.log("\n=== 所有测试完成 ===");
