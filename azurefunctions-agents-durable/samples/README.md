# Combined Agents with Durable Orchestrator Samples

This directory contains samples demonstrating how to use the Azure Functions Agents Durable framework to create and call different types of agents from Durable Functions orchestrators.

## Samples

### [Combined Sample](./combined_sample)

A comprehensive sample that demonstrates how to:
- Create simple HTTP endpoints as an HTTP agent
- Create MCP tools in the same function app
- Call both agent types from a single Durable Functions orchestrator
- Use the new context-first parameter pattern

This is the recommended starting point for understanding the framework.

## Key Concepts

The samples demonstrate several key concepts:

1. **Agent Registration** - How to register HTTP and MCP agents with the framework
2. **Context-First Pattern** - The new API design requiring context as the first parameter
3. **Orchestrator Integration** - How to use agents inside durable orchestrators
4. **MCP Integration** - Working with Model Context Protocol tools

## Getting Started

Each sample includes:
- A README with detailed instructions
- A complete function app implementation
- Required configuration files

Follow the README in each sample directory for specific setup and execution instructions.
