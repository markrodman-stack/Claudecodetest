---
name: azure-functions
description: Build and deploy serverless event-driven applications with Azure Functions. Use when agents need to create, configure, deploy, or debug Azure Functions apps. Covers triggers, bindings, hosting plans, Durable Functions, and deployment across C#, Python, JavaScript, TypeScript, Java, and PowerShell.
---

# Azure Functions

Azure Functions is a serverless compute service that lets you run event-driven code without managing infrastructure. You write functions triggered by events (HTTP requests, queue messages, timers, database changes, etc.) and Azure handles scaling, patching, and infrastructure. You pay only for the compute time your code consumes. Supported languages include C#, Python, JavaScript/TypeScript, Java, PowerShell, and Go (via custom handlers).

## Key Concepts

### Triggers
A trigger defines how a function is invoked. Every function must have exactly one trigger. Triggers also pass data into your function as parameters. Common triggers:

| Trigger | Use Case |
|---------|----------|
| HTTP | REST APIs, webhooks |
| Timer | Scheduled tasks (cron expressions) |
| Queue Storage | Process queue messages |
| Blob Storage | React to file uploads/changes |
| Event Grid / Event Hub | Event-driven architectures, IoT |
| Cosmos DB | Respond to database changes |
| Service Bus | Enterprise messaging |

### Bindings
Bindings declaratively connect functions to other services without writing boilerplate SDK code. They are optional and come in two types:

- **Input bindings** - read data into your function (e.g., read a blob, query Cosmos DB)
- **Output bindings** - write data from your function (e.g., send to queue, write to database)

A function can have multiple input and output bindings. You can always use Azure SDK clients directly instead of bindings.

### Function App
A function app is the deployment and management unit. All functions in a function app share the same configuration, hosting plan, language runtime, and app settings. Key config files:

- **host.json** - runtime and trigger configuration (applies to all functions in the app)
- **local.settings.json** - app settings and connection strings for local development (never commit to source control)

### Hosting Plans

| Plan | Best For | Scale | Key Feature |
|------|----------|-------|-------------|
| **Flex Consumption** (recommended) | New serverless apps | Up to 1,000 instances, per-function scaling | VNet support, configurable memory (512/2048/4096 MB), always-ready instances |
| **Premium** | Production apps needing warm instances | Up to 100 instances | Pre-warmed instances, VNet, unlimited execution time |
| **Dedicated (App Service)** | Existing App Service resources | Manual/autoscale, 10-30 instances | Predictable billing, always-on |
| **Container Apps** | Containerized microservices | Up to 300-1000 instances | Kubernetes-based, GPU support, sidecars |
| **Consumption** (legacy) | Legacy apps | Up to 200 instances | Pay-per-execution, consider migrating to Flex |

### Durable Functions
An extension for writing stateful workflows in a serverless environment. Key patterns:

- **Function chaining** - sequence of activities executed in order
- **Fan-out/fan-in** - run multiple activities in parallel, aggregate results
- **Human interaction** - pause workflow awaiting external events/approval
- **Monitoring** - periodic polling with durable timers
- **Sub-orchestrations** - compose orchestrations from smaller ones

## Project Structure

### C# (.NET Isolated Worker)
```
<project_root>/
 |- Functions/
 |   |- HttpTriggerFunction.cs
 |   |- TimerTriggerFunction.cs
 |- Program.cs
 |- host.json
 |- local.settings.json
 |- *.csproj
```

### Python (v2 model)
```
<project_root>/
 |- function_app.py
 |- host.json
 |- local.settings.json
 |- requirements.txt
```

### Node.js/TypeScript (v4 model)
```
<project_root>/
 |- src/
 |   |- functions/
 |       |- httpTrigger.ts
 |       |- timerTrigger.ts
 |- host.json
 |- local.settings.json
 |- package.json
 |- tsconfig.json
```

## Getting Started

### Prerequisites
- Azure subscription
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) (`npm install -g azure-functions-core-tools@4`)
- Azure CLI (`az`) or Azure PowerShell

### Create a New Project
```bash
# Initialize a new function project
func init MyFunctionApp --worker-runtime <dotnet-isolated|python|node|java|powershell>

# Add a function
func new --name HttpExample --template "HTTP trigger"

# Run locally
func start
```

### local.settings.json (required for local dev)
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "<dotnet-isolated|python|node|java|powershell>"
  }
}
```

## Quick Start Examples

### C# - HTTP Trigger (Isolated Worker)

See [sample_codes/getting-started/http-trigger.cs](sample_codes/getting-started/http-trigger.cs)

### Python - HTTP Trigger (v2 model)

See [sample_codes/getting-started/http-trigger.py](sample_codes/getting-started/http-trigger.py)

### TypeScript - HTTP Trigger (v4 model)

See [sample_codes/getting-started/http-trigger.ts](sample_codes/getting-started/http-trigger.ts)

## Common Patterns

### Timer Trigger (Scheduled Tasks)

See [sample_codes/common-patterns/timer-trigger.py](sample_codes/common-patterns/timer-trigger.py)

### Queue Trigger with Output Binding

See [sample_codes/common-patterns/queue-processing.py](sample_codes/common-patterns/queue-processing.py)

### HTTP with Cosmos DB Output (C#)

See [sample_codes/common-patterns/http-cosmos-output.cs](sample_codes/common-patterns/http-cosmos-output.cs)

## Deployment

### Using Azure Functions Core Tools
```bash
# Deploy to an existing function app
func azure functionapp publish <FunctionAppName>

# Deploy and sync local settings
func azure functionapp publish <FunctionAppName> --publish-local-settings
```

### Using Azure CLI
```bash
# Create a resource group
az group create --name myResourceGroup --location eastus

# Create a storage account
az storage account create --name mystorageaccount --location eastus \
  --resource-group myResourceGroup --sku Standard_LRS

# Create a Flex Consumption function app
az functionapp create --resource-group myResourceGroup \
  --consumption-plan-location eastus \
  --runtime <dotnet-isolated|python|node|java> \
  --functions-version 4 \
  --name <app-name> \
  --storage-account mystorageaccount
```

### Using Azure Developer CLI (azd)
```bash
azd init --template functions-quickstart-<language>-azd
azd up
```

## Key Configurations (host.json)

| Setting | Purpose | Default |
|---------|---------|---------|
| `functionTimeout` | Max execution time per invocation | 5 min (Consumption), 30 min (Premium/Dedicated) |
| `extensions.http.maxConcurrentRequests` | Max concurrent HTTP requests per instance | 100 |
| `extensions.queues.batchSize` | Number of queue messages to process in parallel | 16 |
| `extensions.queues.maxPollingInterval` | Max polling interval for queue trigger | 00:01:00 |
| `extensions.durableTask.storageProvider` | Durable Functions storage backend | Azure Storage |

## Best Practices

- **Write stateless functions**: Store state in external storage, not in-memory variables
- **Write defensive/idempotent functions**: Design for retries and duplicate processing
- **Avoid long-running functions**: Refactor into queue-triggered chains or use Durable Functions
- **Use async code**: Avoid blocking calls; use `async`/`await` (C#, JS/TS, Python)
- **Separate storage accounts**: Use dedicated storage for the function app vs. your data
- **Organize by privilege**: Group functions needing the same credentials in one app
- **Use deployment slots**: Minimize downtime with staging slots and swap
- **Monitor with Application Insights**: Enable for performance metrics and diagnostics

## Pricing & Limits

- **Flex Consumption**: Pay per execution + memory usage during active execution
- **Premium**: Per-core-second + memory, at least one warm instance always running
- **Dedicated**: Fixed App Service plan pricing regardless of executions
- **Consumption**: Pay per execution + execution time + memory used
- **Key limits**: Consumption plan timeout 5 min (configurable to 10), Premium/Dedicated up to unbounded

For current pricing: `microsoft_docs_search(query="Azure Functions pricing")`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cold start latency | Use Flex Consumption with always-ready instances or Premium plan with pre-warmed instances |
| Function timeout | Check hosting plan limits; refactor long operations into Durable Functions |
| Connection exhaustion | Reuse HTTP clients; use static/singleton patterns for SDK clients |
| Missing bindings | Install the correct extension bundle in host.json or NuGet package |
| Deployment failures | Verify `FUNCTIONS_WORKER_RUNTIME` matches your language; check Core Tools version |

For more issues: `microsoft_docs_search(query="Azure Functions troubleshoot <symptom>")`

## Learn More

| Topic | How to Find |
|-------|-------------|
| Supported languages & versions | `microsoft_docs_search(query="Azure Functions supported languages runtime versions")` |
| Triggers & bindings reference | `microsoft_docs_fetch(url="https://learn.microsoft.com/azure/azure-functions/functions-triggers-bindings")` |
| Durable Functions patterns | `microsoft_docs_search(query="Durable Functions patterns orchestration")` |
| Networking & VNet integration | `microsoft_docs_search(query="Azure Functions networking VNet integration")` |
| Security best practices | `microsoft_docs_search(query="Azure Functions security best practices managed identity")` |
| Monitoring & diagnostics | `microsoft_docs_search(query="Azure Functions monitoring Application Insights")` |
| Hosting plan comparison | `microsoft_docs_fetch(url="https://learn.microsoft.com/azure/azure-functions/functions-scale")` |
| Flex Consumption plan | `microsoft_docs_fetch(url="https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan")` |
| Infrastructure as Code (Bicep) | `microsoft_docs_search(query="Azure Functions Bicep template deployment")` |
| Code samples | `microsoft_code_sample_search(query="Azure Functions <scenario>", language="<lang>")` |

## CLI Alternative

If the Learn MCP server is not available, use the `mslearn` CLI instead:

| MCP Tool | CLI Command |
|----------|-------------|
| `microsoft_docs_search(query: "...")` | `mslearn search "..."` |
| `microsoft_code_sample_search(query: "...", language: "...")` | `mslearn code-search "..." --language ...` |
| `microsoft_docs_fetch(url: "...")` | `mslearn fetch "..."` |

Run directly with `npx @microsoft/learn-cli <command>` or install globally with `npm install -g @microsoft/learn-cli`.
