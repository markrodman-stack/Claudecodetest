// Azure Functions HTTP Trigger with Cosmos DB Output Binding
// C# Isolated Worker Model (.NET 8)
//
// Prerequisites:
//   dotnet add package Microsoft.Azure.Functions.Worker.Extensions.CosmosDB
//
// Required app setting:
//   "CosmosDBConnection": "<your-cosmos-db-connection-string>"
//
// This function receives an HTTP request and writes a document to Cosmos DB.

using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace MyFunctionApp
{
    // Return type for multiple output bindings
    public class MultiResponse
    {
        [CosmosDBOutput(
            databaseName: "my-database",
            containerName: "my-container",
            Connection = "CosmosDBConnection")]
        public MyDocument Document { get; set; }

        public IActionResult HttpResponse { get; set; }
    }

    public class MyDocument
    {
        public string id { get; set; }
        public string message { get; set; }
        public DateTime createdAt { get; set; }
    }

    public class HttpCosmosFunction
    {
        private readonly ILogger<HttpCosmosFunction> _logger;

        public HttpCosmosFunction(ILogger<HttpCosmosFunction> logger)
        {
            _logger = logger;
        }

        [Function("CreateDocument")]
        public async Task<MultiResponse> Run(
            [HttpTrigger(AuthorizationLevel.Function, "post")] HttpRequest req)
        {
            _logger.LogInformation("Creating new Cosmos DB document from HTTP request.");

            // Read message from request body
            using var reader = new StreamReader(req.Body);
            string requestBody = await reader.ReadToEndAsync();
            var data = JsonSerializer.Deserialize<JsonElement>(requestBody);
            string message = data.TryGetProperty("message", out var msgElement)
                ? msgElement.GetString()
                : "Default message";

            var newDocument = new MyDocument
            {
                id = Guid.NewGuid().ToString(),
                message = message,
                createdAt = DateTime.UtcNow
            };

            // Return both the HTTP response and the Cosmos DB document
            return new MultiResponse
            {
                Document = newDocument,
                HttpResponse = new OkObjectResult(newDocument)
            };
        }
    }
}
