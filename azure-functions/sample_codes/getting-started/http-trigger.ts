// Azure Functions HTTP Trigger - TypeScript Node.js v4 Programming Model
//
// Prerequisites:
//   npm install @azure/functions
//
// Run locally: npm start (or func start)
// Test: GET http://localhost:7071/api/httpTrigger?name=World
//       POST http://localhost:7071/api/httpTrigger (body: "World")

import {
  app,
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";

export async function httpTrigger(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  context.log(`Http function processed request for url "${request.url}"`);

  const name =
    request.query.get("name") || (await request.text()) || "world";

  return { body: `Hello, ${name}!` };
}

app.http("httpTrigger", {
  methods: ["GET", "POST"],
  authLevel: "anonymous",
  handler: httpTrigger,
});
