// Azure Functions HTTP Trigger - C# Isolated Worker Model (.NET 8)
//
// Prerequisites:
//   dotnet add package Microsoft.Azure.Functions.Worker
//   dotnet add package Microsoft.Azure.Functions.Worker.Sdk
//   dotnet add package Microsoft.Azure.Functions.Worker.Extensions.Http.AspNetCore
//
// Run locally: func start
// Test: GET http://localhost:7071/api/HttpExample?name=World
//       POST http://localhost:7071/api/HttpExample (body: {"name": "World"})

using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace MyFunctionApp
{
    public class HttpExample
    {
        private readonly ILogger<HttpExample> _logger;

        public HttpExample(ILogger<HttpExample> logger)
        {
            _logger = logger;
        }

        [Function("HttpExample")]
        public async Task<IActionResult> Run(
            [HttpTrigger(AuthorizationLevel.Anonymous, "get", "post")] HttpRequest req)
        {
            _logger.LogInformation("C# HTTP trigger function processed a request.");

            // Read name from query string
            string name = req.Query["name"];

            // Or read from request body
            if (string.IsNullOrEmpty(name))
            {
                using var reader = new StreamReader(req.Body);
                string requestBody = await reader.ReadToEndAsync();
                if (!string.IsNullOrEmpty(requestBody))
                {
                    var data = JsonSerializer.Deserialize<JsonElement>(requestBody);
                    if (data.TryGetProperty("name", out var nameElement))
                    {
                        name = nameElement.GetString();
                    }
                }
            }

            return string.IsNullOrEmpty(name)
                ? new OkObjectResult("Pass a name in the query string or request body.")
                : new OkObjectResult($"Hello, {name}!");
        }
    }
}
